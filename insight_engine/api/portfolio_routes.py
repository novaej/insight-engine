from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.ai.handlers import generate_explanation
from insight_engine.api.asset_routes import _to_record
from insight_engine.api.schemas import (
    DimensionsResponse,
    InsightResponse,
    MetricsResponse,
    PortfolioRequest,
    PortfolioSummaryResponse,
)
from insight_engine.database import get_session
from insight_engine.domain.entities import UserProfile
from insight_engine.domain.enums import RiskLevel
from insight_engine.services.analysis import analyze_asset

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


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

    insights = []
    for asset in request.assets:
        try:
            insight = analyze_asset(asset.ticker, user_profile)
            if request.use_ai:
                insight = generate_explanation(insight, user_profile)
            insights.append(insight)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed for {asset.ticker}: {str(e)}",
            )

    for insight in insights:
        session.add(_to_record(insight))
    await session.commit()

    overall_risk = _determine_overall_risk(insights)
    summary = _build_summary(insights, overall_risk)

    insight_responses = [
        InsightResponse(
            ticker=i.ticker,
            asset_state=i.asset_state,
            dimensions=DimensionsResponse(
                trend=i.dimensions.trend,
                valuation=i.dimensions.valuation,
                fundamentals=i.dimensions.fundamentals,
                risk_level=i.dimensions.risk_level,
                market_context=i.dimensions.market_context,
            ),
            metrics=MetricsResponse(
                current_price=i.metrics.current_price,
                sma_50=i.metrics.sma_50,
                sma_200=i.metrics.sma_200,
                pe_ratio=i.metrics.pe_ratio,
                revenue_growth=i.metrics.revenue_growth,
                profit_margin=i.metrics.profit_margin,
                debt_to_equity=i.metrics.debt_to_equity,
                annualized_volatility=i.metrics.annualized_volatility,
                max_drawdown=i.metrics.max_drawdown,
            ),
            horizon=i.horizon,
            scenario=i.scenario,
            risks=i.risks,
            explanation=i.explanation,
        )
        for i in insights
    ]

    return PortfolioSummaryResponse(
        total_assets=len(insights),
        insights=insight_responses,
        overall_risk=overall_risk,
        summary=summary,
    )


def _determine_overall_risk(insights) -> RiskLevel:
    """Determine portfolio-level risk from individual insights."""
    from insight_engine.domain.enums import AssetState

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
    from insight_engine.domain.enums import AssetState

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
