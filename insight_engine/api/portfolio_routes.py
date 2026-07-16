import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.ai.handlers import generate_batch_explanations
from insight_engine.api.asset_routes import _build_insight_response, _to_record
from insight_engine.api.schemas import (
    AlternativeResponse,
    AlternativesResponse,
    DimensionsResponse,
    InsightResponse,
    MetricsResponse,
    PortfolioAsset,
    PortfolioRequest,
    PortfolioResponse,
    PortfolioSummaryResponse,
    PortfolioUpdateRequest,
    UserProfileRequest,
)
from insight_engine.database import get_session
from insight_engine.domain.entities import Insight, UserProfile
from insight_engine.domain.enums import (
    AssetState,
    Fundamentals,
    Horizon,
    MarketContext,
    RiskLevel,
    Trend,
    Valuation,
)
from insight_engine.domain.models import InsightRecord, Portfolio
from insight_engine.providers import get_market_data_provider
from insight_engine.services.alternatives import prepare_alternatives_context, resolve_alternatives
from insight_engine.services.analysis import analyze_asset
from insight_engine.services.translator import translate_insight, translate_texts

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


async def _run_analysis(
    assets: list[PortfolioAsset],
    user_profile: UserProfile,
    use_ai: bool,
    language: str | None,
    session: AsyncSession,
    portfolio_id: int,
) -> tuple[list[Insight], RiskLevel, str]:
    """Run analysis on all assets, persist insights, and return results."""
    market_data_provider = get_market_data_provider()

    # Fetch the S&P 500 history once; it's identical for every asset.
    sp500_hist = await asyncio.to_thread(
        market_data_provider.fetch_history, "^GSPC", "1y"
    )

    # Deterministic analysis is I/O-bound (market data fetches); run assets
    # concurrently in threads, capped to stay polite to the data provider.
    semaphore = asyncio.Semaphore(5)

    def _analyze_one_sync(asset: PortfolioAsset) -> tuple[Insight, dict | None]:
        insight, info = analyze_asset(
            asset.ticker, user_profile, market_data_provider, sp500_hist=sp500_hist
        )
        alternatives_ctx = prepare_alternatives_context(
            insight, info, user_profile, market_data_provider
        )
        return insight, alternatives_ctx

    async def _analyze_one(asset: PortfolioAsset) -> tuple[Insight, dict | None]:
        async with semaphore:
            try:
                return await asyncio.to_thread(_analyze_one_sync, asset)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Analysis failed for {asset.ticker}: {str(e)}",
                )

    analyzed = await asyncio.gather(*(_analyze_one(asset) for asset in assets))

    if use_ai:
        # One LLM call covers explanations (and alternative suggestions where
        # triggered) for the whole portfolio.
        await asyncio.to_thread(generate_batch_explanations, analyzed, user_profile)
        if language:
            for insight, _ in analyzed:
                await asyncio.to_thread(translate_insight, insight, language)

    async def _resolve_one(insight: Insight, alternatives_ctx: dict) -> None:
        async with semaphore:
            try:
                await asyncio.to_thread(
                    resolve_alternatives,
                    insight,
                    user_profile,
                    market_data_provider,
                    alternatives_ctx,
                    use_ai,
                    sp500_hist,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Analysis failed for {insight.ticker}: {str(e)}",
                )

    await asyncio.gather(
        *(
            _resolve_one(insight, ctx)
            for insight, ctx in analyzed
            if ctx is not None
        )
    )

    insights: list[Insight] = [insight for insight, _ in analyzed]

    # Delete old insights for this portfolio
    await session.execute(
        delete(InsightRecord).where(InsightRecord.portfolio_id == portfolio_id)
    )

    # Save new insights
    for insight in insights:
        record = _to_record(insight)
        record.portfolio_id = portfolio_id
        session.add(record)

    overall_risk = _determine_overall_risk(insights)
    summary = _build_summary(insights, overall_risk)
    if language:
        summary = translate_texts([summary], language)[0]

    return insights, overall_risk, summary


@router.post("/analyze", response_model=PortfolioSummaryResponse)
async def analyze_portfolio_endpoint(
    request: PortfolioRequest,
    session: AsyncSession = Depends(get_session),
):
    """Analyze all assets in a portfolio and return a summary."""
    user_profile = UserProfile(
        risk=request.user_profile.risk,
        horizon=request.user_profile.horizon,
        objective=request.user_profile.goal,
    )

    # Upsert the single portfolio row
    result = await session.execute(select(Portfolio).limit(1))
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        portfolio = Portfolio(
            user_profile=request.user_profile.model_dump(),
            assets=[a.model_dump() for a in request.assets],
        )
        session.add(portfolio)
        await session.flush()  # get the id
    else:
        portfolio.user_profile = request.user_profile.model_dump()
        portfolio.assets = [a.model_dump() for a in request.assets]

    insights, overall_risk, summary = await _run_analysis(
        assets=request.assets,
        user_profile=user_profile,
        use_ai=request.use_ai,
        language=request.language,
        session=session,
        portfolio_id=portfolio.id,
    )

    portfolio.overall_risk = overall_risk.value
    portfolio.summary = summary
    await session.commit()

    return PortfolioSummaryResponse(
        total_assets=len(insights),
        insights=[_build_insight_response(i) for i in insights],
        overall_risk=overall_risk,
        summary=summary,
    )


@router.get("", response_model=PortfolioResponse)
async def get_portfolio_endpoint(
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the current portfolio with its latest insights."""
    result = await session.execute(select(Portfolio).limit(1))
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        raise HTTPException(status_code=404, detail="No portfolio found")

    records_result = await session.execute(
        select(InsightRecord).where(InsightRecord.portfolio_id == portfolio.id)
    )
    records = records_result.scalars().all()

    insight_responses = [_record_to_response(r) for r in records]

    return PortfolioResponse(
        id=portfolio.id,
        user_profile=UserProfileRequest(**portfolio.user_profile),
        assets=[PortfolioAsset(**a) for a in portfolio.assets],
        overall_risk=RiskLevel(portfolio.overall_risk) if portfolio.overall_risk else RiskLevel.low,
        summary=portfolio.summary or "",
        insights=insight_responses,
        updated_at=portfolio.updated_at,
    )


@router.put("", response_model=PortfolioSummaryResponse)
async def update_portfolio_endpoint(
    request: PortfolioUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update the portfolio assets (and optionally user profile) and re-analyze."""
    result = await session.execute(select(Portfolio).limit(1))
    portfolio = result.scalar_one_or_none()

    if portfolio is None:
        raise HTTPException(status_code=404, detail="No portfolio found")

    # Update assets
    portfolio.assets = [a.model_dump() for a in request.assets]

    # Update user profile if provided
    if request.user_profile is not None:
        portfolio.user_profile = request.user_profile.model_dump()

    user_profile_data = UserProfileRequest(**portfolio.user_profile)
    user_profile = UserProfile(
        risk=user_profile_data.risk,
        horizon=user_profile_data.horizon,
        objective=user_profile_data.goal,
    )

    insights, overall_risk, summary = await _run_analysis(
        assets=request.assets,
        user_profile=user_profile,
        use_ai=request.use_ai,
        language=request.language,
        session=session,
        portfolio_id=portfolio.id,
    )

    portfolio.overall_risk = overall_risk.value
    portfolio.summary = summary
    await session.commit()

    return PortfolioSummaryResponse(
        total_assets=len(insights),
        insights=[_build_insight_response(i) for i in insights],
        overall_risk=overall_risk,
        summary=summary,
    )


def _record_to_response(record: InsightRecord) -> InsightResponse:
    """Convert a persisted InsightRecord back to an InsightResponse."""
    dims = record.dimensions
    mets = record.metrics or {}

    alternatives_resp = None
    if record.alternatives and record.alternatives.get("triggered"):
        alternatives_resp = AlternativesResponse(
            triggered=True,
            trigger_reasons=record.alternatives.get("trigger_reasons", []),
            suggestions=[
                AlternativeResponse(
                    ticker=s["ticker"],
                    health_score=s.get("health_score"),
                    reason=s.get("reason", ""),
                )
                for s in record.alternatives.get("suggestions", [])
            ],
        )

    return InsightResponse(
        ticker=record.ticker,
        asset_state=AssetState(record.asset_state),
        dimensions=DimensionsResponse(
            trend=Trend(dims["trend"]),
            valuation=Valuation(dims["valuation"]),
            fundamentals=Fundamentals(dims["fundamentals"]),
            risk_level=RiskLevel(dims["risk_level"]),
            market_context=MarketContext(dims["market_context"]),
        ),
        metrics=MetricsResponse(
            current_price=mets.get("current_price"),
            sma_50=mets.get("sma_50"),
            sma_200=mets.get("sma_200"),
            parabolic_sar=mets.get("parabolic_sar"),
            pe_ratio=mets.get("pe_ratio"),
            revenue_growth=mets.get("revenue_growth"),
            profit_margin=mets.get("profit_margin"),
            debt_to_equity=mets.get("debt_to_equity"),
            annualized_volatility=mets.get("annualized_volatility"),
            max_drawdown=mets.get("max_drawdown"),
        ),
        horizon=Horizon(record.horizon),
        scenario=record.scenario or "",
        risks=record.risks or [],
        explanation=record.explanation or "",
        portfolio_role=record.portfolio_role,
        health_score=record.health_score,
        profile_fit_score=record.profile_fit_score,
        alternatives=alternatives_resp,
    )


def _determine_overall_risk(insights) -> RiskLevel:
    """Determine portfolio-level risk from individual insights."""
    high_risk_count = sum(
        1
        for i in insights
        if i.asset_state in (AssetState.risky, AssetState.unattractive)
    )

    if high_risk_count > len(insights) / 2:
        return RiskLevel.high
    elif high_risk_count > 0:
        return RiskLevel.medium
    else:
        return RiskLevel.low


def _build_summary(insights, overall_risk: RiskLevel) -> str:
    """Build a brief portfolio summary string."""
    states = [i.asset_state for i in insights]
    healthy = sum(1 for s in states if s in (AssetState.healthy, AssetState.healthy_but_expensive))
    risky = sum(1 for s in states if s in (AssetState.risky, AssetState.unattractive))
    neutral = sum(1 for s in states if s == AssetState.neutral)

    parts = []
    if healthy:
        parts.append(f"{healthy} asset(s) in healthy condition")
    if neutral:
        parts.append(f"{neutral} asset(s) in neutral state")
    if risky:
        parts.append(f"{risky} asset(s) showing elevated risk")

    summary = "; ".join(parts) if parts else "Portfolio analysis complete"
    summary += f". Overall portfolio risk level: {overall_risk.value}."
    return summary
