import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.adapters.caching import CachingMarketDataProvider
from insight_engine.ai.handlers import generate_batch_explanations
from insight_engine.api.asset_routes import _build_insight_response, _to_record
from insight_engine.api.deps import get_current_user, get_user_portfolio
from insight_engine.api.schemas import (
    AlternativeResponse,
    AlternativesResponse,
    ConcentrationResponse,
    DimensionsResponse,
    InsightResponse,
    MetricsResponse,
    PortfolioAsset,
    PortfolioRequest,
    PortfolioResponse,
    PortfolioSummaryResponse,
    PortfolioUpdateRequest,
    PositionContextResponse,
    PositionResponse,
    UserProfileRequest,
)
from insight_engine.database import get_session
from insight_engine.domain.entities import (
    AlternativesResult,
    ConcentrationResult,
    Insight,
    UserProfile,
)
from insight_engine.domain.enums import (
    AssetState,
    Fundamentals,
    Horizon,
    MarketContext,
    RiskLevel,
    Trend,
    Valuation,
)
from insight_engine.domain.models import InsightRecord, Position, User
from insight_engine.providers import get_market_data_provider
from insight_engine.rules.concentration_rules import (
    compute_position_contexts,
    determine_weighted_risk,
    evaluate_concentration,
)
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
    include_alternatives: bool = True,
) -> tuple[list[Insight], RiskLevel, str, float | None, ConcentrationResult]:
    """Run analysis on all assets, persist insights, and return results.

    Insights are appended, never deleted — older rows form the history.
    Returns (insights, overall_risk, summary, total_value, concentration).
    """
    # Request-scoped cache: assets sharing a role benchmark (and candidate
    # validations) reuse the same fetches across worker threads.
    market_data_provider = CachingMarketDataProvider(get_market_data_provider())

    # Deterministic analysis is I/O-bound (market data fetches); run assets
    # concurrently in threads, capped to stay polite to the data provider.
    semaphore = asyncio.Semaphore(5)

    def _analyze_one_sync(asset: PortfolioAsset) -> tuple[Insight, dict | None]:
        insight, info = analyze_asset(asset.ticker, user_profile, market_data_provider)
        # Always prepare context (sets role/scores/news on the insight); the
        # include_alternatives flag only gates candidate resolution below.
        alternatives_ctx = prepare_alternatives_context(
            insight, info, user_profile, market_data_provider
        )
        if not include_alternatives:
            alternatives_ctx = None
            insight.alternatives = AlternativesResult(triggered=False)
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

    # Position-aware context: weights, unrealized gain/loss, concentration.
    # Computed before the AI call so the prompt can reference exposure.
    insights: list[Insight] = [insight for insight, _ in analyzed]
    total_value = compute_position_contexts(assets, insights)
    concentration = evaluate_concentration(insights)

    if use_ai:
        # One LLM call covers explanations (and alternative suggestions where
        # triggered) for the whole portfolio.
        await asyncio.to_thread(
            generate_batch_explanations,
            analyzed,
            user_profile,
            None,
            total_value,
            concentration,
        )
        if language:
            for insight, _ in analyzed:
                await asyncio.to_thread(translate_insight, insight, language)

    held_tickers = {insight.ticker.upper() for insight in insights}

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
                    held_tickers,
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

    # Append new insights; history is kept
    for insight in insights:
        record = _to_record(insight)
        record.portfolio_id = portfolio_id
        session.add(record)

    overall_risk = determine_weighted_risk(insights)
    summary = _build_summary(insights, overall_risk, total_value, concentration)
    if language:
        summary = translate_texts([summary], language)[0]

    return insights, overall_risk, summary, total_value, concentration


MAX_TICKERS = 20


def _aggregate_lots(assets: list[PortfolioAsset]) -> list[PortfolioAsset]:
    """Collapse purchase lots into one entry per ticker for analysis.

    Quantity is summed; purchase price becomes the weighted average over the
    lots that have one.
    """
    by_ticker: dict[str, list[PortfolioAsset]] = {}
    for asset in assets:
        by_ticker.setdefault(asset.ticker.upper(), []).append(asset)

    aggregated = []
    for ticker, lots in sorted(by_ticker.items()):
        priced = [lot for lot in lots if lot.purchase_price is not None]
        avg_price = None
        if priced:
            priced_qty = sum(lot.quantity for lot in priced)
            avg_price = (
                sum(lot.quantity * lot.purchase_price for lot in priced) / priced_qty
            )
        aggregated.append(
            PortfolioAsset(
                ticker=ticker,
                quantity=sum(lot.quantity for lot in lots),
                purchase_price=avg_price,
            )
        )
    return aggregated


def _check_ticker_limit(assets: list[PortfolioAsset]) -> None:
    tickers = {a.ticker.upper() for a in assets}
    if len(tickers) > MAX_TICKERS:
        raise HTTPException(
            status_code=422,
            detail=f"Portfolio is limited to {MAX_TICKERS} distinct tickers",
        )


async def _sync_positions(
    portfolio_id: int, assets: list[PortfolioAsset], session: AsyncSession
) -> None:
    """Replace stored lots with the requested list (full desired state).

    Each entry is one lot; repeating a ticker creates multiple lots. Lots of
    tickers absent from the request are removed.
    """
    result = await session.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )
    for position in result.scalars().all():
        await session.delete(position)

    for asset in assets:
        session.add(
            Position(
                portfolio_id=portfolio_id,
                ticker=asset.ticker.upper(),
                quantity=asset.quantity,
                purchase_price=asset.purchase_price,
                purchase_date=asset.purchase_date,
            )
        )


async def _load_position_assets(
    portfolio_id: int, session: AsyncSession
) -> list[PortfolioAsset]:
    """Load stored lots aggregated per ticker, ready for analysis."""
    result = await session.execute(
        select(Position)
        .where(Position.portfolio_id == portfolio_id)
        .order_by(Position.ticker)
    )
    lots = [
        PortfolioAsset(
            ticker=p.ticker,
            quantity=p.quantity,
            purchase_price=p.purchase_price,
            purchase_date=p.purchase_date,
        )
        for p in result.scalars().all()
    ]
    return _aggregate_lots(lots)


@router.post("/analyze", response_model=PortfolioSummaryResponse)
async def analyze_portfolio_endpoint(
    request: PortfolioRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Analyze the portfolio and return a summary.

    When `assets` is provided, the stored positions are synced to it first;
    when omitted, the stored positions are analyzed.
    """
    user_profile = UserProfile(
        risk=request.user_profile.risk,
        horizon=request.user_profile.horizon,
        objective=request.user_profile.goal,
    )

    portfolio = await get_user_portfolio(user, session, create=True)
    portfolio.user_profile = request.user_profile.model_dump()

    if request.assets is not None:
        _check_ticker_limit(request.assets)
        await _sync_positions(portfolio.id, request.assets, session)
        assets = _aggregate_lots(request.assets)
    else:
        assets = await _load_position_assets(portfolio.id, session)
        if not assets:
            raise HTTPException(
                status_code=400,
                detail="No stored positions to analyze; provide `assets` or add positions first",
            )

    insights, overall_risk, summary, total_value, concentration = await _run_analysis(
        assets=assets,
        user_profile=user_profile,
        use_ai=request.use_ai,
        language=request.language,
        session=session,
        portfolio_id=portfolio.id,
        include_alternatives=request.include_alternatives,
    )

    portfolio.overall_risk = overall_risk.value
    portfolio.summary = summary
    portfolio.total_value = total_value
    portfolio.concentration = _concentration_to_json(concentration)
    await session.commit()

    return PortfolioSummaryResponse(
        total_assets=len(insights),
        insights=[_build_insight_response(i) for i in insights],
        overall_risk=overall_risk,
        summary=summary,
        total_value=total_value,
        concentration=_concentration_to_response(concentration),
    )


@router.get("", response_model=PortfolioResponse)
async def get_portfolio_endpoint(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the user's portfolio with the latest insight per held ticker."""
    portfolio = await get_user_portfolio(user, session)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="No portfolio found")

    positions_result = await session.execute(
        select(Position)
        .where(Position.portfolio_id == portfolio.id)
        .order_by(Position.ticker)
    )
    positions = positions_result.scalars().all()
    tickers = [p.ticker for p in positions]

    records = []
    if tickers:
        latest = (
            select(func.max(InsightRecord.id).label("max_id"))
            .where(
                InsightRecord.portfolio_id == portfolio.id,
                InsightRecord.ticker.in_(tickers),
            )
            .group_by(InsightRecord.ticker)
            .subquery()
        )
        records_result = await session.execute(
            select(InsightRecord).where(InsightRecord.id.in_(select(latest.c.max_id)))
        )
        records = records_result.scalars().all()

    return PortfolioResponse(
        id=portfolio.id,
        user_profile=UserProfileRequest(**portfolio.user_profile),
        assets=[
            PositionResponse(
                id=p.id,
                ticker=p.ticker,
                quantity=p.quantity,
                purchase_price=p.purchase_price,
                purchase_date=p.purchase_date,
                updated_at=p.updated_at,
            )
            for p in positions
        ],
        overall_risk=RiskLevel(portfolio.overall_risk) if portfolio.overall_risk else RiskLevel.low,
        summary=portfolio.summary or "",
        insights=[_record_to_response(r) for r in records],
        updated_at=portfolio.updated_at,
        total_value=portfolio.total_value,
        concentration=_concentration_to_response(portfolio.concentration),
    )


@router.put("", response_model=PortfolioSummaryResponse)
async def update_portfolio_endpoint(
    request: PortfolioUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update the portfolio assets (and optionally user profile) and re-analyze."""
    portfolio = await get_user_portfolio(user, session)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="No portfolio found")

    _check_ticker_limit(request.assets)
    await _sync_positions(portfolio.id, request.assets, session)

    if request.user_profile is not None:
        portfolio.user_profile = request.user_profile.model_dump()

    user_profile_data = UserProfileRequest(**portfolio.user_profile)
    user_profile = UserProfile(
        risk=user_profile_data.risk,
        horizon=user_profile_data.horizon,
        objective=user_profile_data.goal,
    )

    insights, overall_risk, summary, total_value, concentration = await _run_analysis(
        assets=_aggregate_lots(request.assets),
        user_profile=user_profile,
        use_ai=request.use_ai,
        language=request.language,
        session=session,
        portfolio_id=portfolio.id,
        include_alternatives=request.include_alternatives,
    )

    portfolio.overall_risk = overall_risk.value
    portfolio.summary = summary
    portfolio.total_value = total_value
    portfolio.concentration = _concentration_to_json(concentration)
    await session.commit()

    return PortfolioSummaryResponse(
        total_assets=len(insights),
        insights=[_build_insight_response(i) for i in insights],
        overall_risk=overall_risk,
        summary=summary,
        total_value=total_value,
        concentration=_concentration_to_response(concentration),
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
                    profile_fit_score=s.get("profile_fit_score"),
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
            benchmark_ticker=mets.get("benchmark_ticker"),
            benchmark_above_sma200=mets.get("benchmark_above_sma200"),
        ),
        horizon=Horizon(record.horizon),
        scenario=record.scenario or "",
        risks=record.risks or [],
        explanation=record.explanation or "",
        portfolio_role=record.portfolio_role,
        health_score=record.health_score,
        profile_fit_score=record.profile_fit_score,
        alternatives=alternatives_resp,
        analyzed_at=record.created_at,
        position=PositionContextResponse(**record.position_context)
        if record.position_context
        else None,
    )


def _concentration_to_json(concentration: ConcentrationResult | None) -> dict | None:
    if concentration is None:
        return None
    return {
        "state": concentration.state.value,
        "flagged_tickers": concentration.flagged_tickers,
        "flagged_roles": concentration.flagged_roles,
    }


def _concentration_to_response(concentration) -> ConcentrationResponse | None:
    """Accepts a ConcentrationResult entity or the stored JSON dict."""
    if concentration is None:
        return None
    if isinstance(concentration, dict):
        return ConcentrationResponse(
            state=concentration.get("state", ""),
            flagged_tickers=concentration.get("flagged_tickers", []),
            flagged_roles=concentration.get("flagged_roles", []),
        )
    return ConcentrationResponse(
        state=concentration.state.value,
        flagged_tickers=concentration.flagged_tickers,
        flagged_roles=concentration.flagged_roles,
    )


def _build_summary(
    insights,
    overall_risk: RiskLevel,
    total_value: float | None = None,
    concentration: ConcentrationResult | None = None,
) -> str:
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
    if total_value is not None:
        summary += f" Total portfolio value: {total_value:,.2f}."
    if concentration is not None and concentration.flagged_tickers:
        flagged = ", ".join(concentration.flagged_tickers)
        summary += f" Concentrated exposure: {flagged} above 25% of portfolio value."
    if concentration is not None and concentration.flagged_roles:
        flagged = ", ".join(concentration.flagged_roles)
        summary += f" Role concentration: {flagged} above 40% of portfolio value."
    return summary
