from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.adapters.caching import CachingMarketDataProvider
from insight_engine.ai.handlers import generate_explanation
from insight_engine.api.schemas import (
    AlternativeResponse,
    AlternativesResponse,
    AnalyzeAssetRequest,
    DimensionsResponse,
    InsightResponse,
    MetricsResponse,
    NewsFlagsResponse,
    PositionContextResponse,
)
from insight_engine.database import get_session
from insight_engine.domain.entities import AlternativesResult, Insight, UserProfile
from insight_engine.providers import get_market_data_provider
from insight_engine.services.alternatives import prepare_alternatives_context, resolve_alternatives
from insight_engine.services.analysis import analyze_asset
from insight_engine.services.insight_store import insight_to_record
from insight_engine.services.translator import translate_insight

router = APIRouter(prefix="/assets", tags=["assets"])

# Re-export so existing importers (portfolio_routes) keep working.
_to_record = insight_to_record


@router.post("/analyze", response_model=InsightResponse)
async def analyze_asset_endpoint(
    request: AnalyzeAssetRequest,
    session: AsyncSession = Depends(get_session),
):
    """Analyze a single asset and return an educational insight."""
    user_profile = None
    if request.user_profile:
        user_profile = UserProfile(
            risk=request.user_profile.risk,
            horizon=request.user_profile.horizon,
            objective=request.user_profile.goal,
        )

    try:
        market_data_provider = CachingMarketDataProvider(get_market_data_provider())
        insight, info = analyze_asset(request.ticker, user_profile, market_data_provider)

        # Prepare alternatives context (scores, role, news, trigger check).
        # Always run when a profile is present so scores/role/news populate the
        # insight; the include_alternatives flag only gates candidate resolution.
        alternatives_ctx = None
        if user_profile:
            alternatives_ctx = prepare_alternatives_context(
                insight, info, user_profile, market_data_provider
            )
            if not request.include_alternatives:
                alternatives_ctx = None
                insight.alternatives = AlternativesResult(triggered=False)

        if request.use_ai:
            insight = generate_explanation(
                insight, user_profile, alternatives_context=alternatives_ctx
            )
            if request.language:
                translate_insight(insight, request.language)

        # Resolve alternatives if triggered
        if alternatives_ctx and user_profile:
            resolve_alternatives(
                insight, user_profile, market_data_provider, alternatives_ctx, request.use_ai
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    record = _to_record(insight)
    session.add(record)
    await session.commit()

    return _build_insight_response(insight)


def _build_insight_response(insight: Insight) -> InsightResponse:
    """Build an InsightResponse from an Insight entity."""
    alternatives_resp = None
    if insight.alternatives and insight.alternatives.triggered:
        alternatives_resp = AlternativesResponse(
            triggered=True,
            trigger_reasons=insight.alternatives.trigger_reasons,
            suggestions=[
                AlternativeResponse(
                    ticker=s.ticker,
                    health_score=s.health_score,
                    profile_fit_score=s.profile_fit_score,
                    reason=s.reason,
                )
                for s in insight.alternatives.suggestions
            ],
        )

    return InsightResponse(
        ticker=insight.ticker,
        asset_state=insight.asset_state,
        dimensions=DimensionsResponse(
            trend=insight.dimensions.trend,
            valuation=insight.dimensions.valuation,
            fundamentals=insight.dimensions.fundamentals,
            risk_level=insight.dimensions.risk_level,
            market_context=insight.dimensions.market_context,
        ),
        metrics=MetricsResponse(
            current_price=insight.metrics.current_price,
            sma_50=insight.metrics.sma_50,
            sma_200=insight.metrics.sma_200,
            parabolic_sar=insight.metrics.parabolic_sar,
            pe_ratio=insight.metrics.pe_ratio,
            revenue_growth=insight.metrics.revenue_growth,
            profit_margin=insight.metrics.profit_margin,
            debt_to_equity=insight.metrics.debt_to_equity,
            dividend_yield=insight.metrics.dividend_yield,
            annualized_volatility=insight.metrics.annualized_volatility,
            max_drawdown=insight.metrics.max_drawdown,
            benchmark_ticker=insight.metrics.benchmark_ticker,
            benchmark_above_sma200=insight.metrics.benchmark_above_sma200,
        ),
        horizon=insight.horizon,
        scenario=insight.scenario,
        risks=insight.risks,
        explanation=insight.explanation,
        portfolio_role=insight.portfolio_role.value if insight.portfolio_role else None,
        health_score=insight.scores.health_score if insight.scores else None,
        profile_fit_score=insight.scores.profile_fit_score if insight.scores else None,
        alternatives=alternatives_resp,
        position=PositionContextResponse(
            quantity=insight.position.quantity,
            market_value=insight.position.market_value,
            weight=insight.position.weight,
            avg_purchase_price=insight.position.avg_purchase_price,
            unrealized_gain_pct=insight.position.unrealized_gain_pct,
        )
        if insight.position
        else None,
        news_flags=NewsFlagsResponse(
            regulatory_risk=insight.news_flags.regulatory_risk,
            earnings_negative=insight.news_flags.earnings_negative,
            management_change=insight.news_flags.management_change,
            litigation_risk=insight.news_flags.litigation_risk,
        )
        if insight.news_flags
        else None,
    )
