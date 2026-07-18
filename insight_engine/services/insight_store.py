"""Persistence mapping for insights.

Central place to turn an Insight entity into an InsightRecord and append it to a
portfolio's history — reused by the asset/portfolio endpoints and the monitoring
sweep so the serialized shape stays consistent.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.domain.entities import Insight
from insight_engine.domain.models import InsightRecord


def insight_to_record(insight: Insight) -> InsightRecord:
    """Convert an Insight entity to a database record."""
    alternatives_json = None
    if insight.alternatives and insight.alternatives.triggered:
        alternatives_json = {
            "triggered": True,
            "trigger_reasons": insight.alternatives.trigger_reasons,
            "suggestions": [
                {
                    "ticker": s.ticker,
                    "health_score": s.health_score,
                    "profile_fit_score": s.profile_fit_score,
                    "reason": s.reason,
                }
                for s in insight.alternatives.suggestions
            ],
        }

    position_json = None
    if insight.position is not None:
        position_json = {
            "quantity": insight.position.quantity,
            "market_value": insight.position.market_value,
            "weight": insight.position.weight,
            "avg_purchase_price": insight.position.avg_purchase_price,
            "unrealized_gain_pct": insight.position.unrealized_gain_pct,
        }

    news_json = None
    if insight.news_flags is not None:
        news_json = {
            "regulatory_risk": insight.news_flags.regulatory_risk,
            "earnings_negative": insight.news_flags.earnings_negative,
            "management_change": insight.news_flags.management_change,
            "litigation_risk": insight.news_flags.litigation_risk,
        }

    return InsightRecord(
        ticker=insight.ticker,
        asset_state=insight.asset_state.value,
        dimensions={
            "trend": insight.dimensions.trend.value,
            "valuation": insight.dimensions.valuation.value,
            "fundamentals": insight.dimensions.fundamentals.value,
            "risk_level": insight.dimensions.risk_level.value,
            "market_context": insight.dimensions.market_context.value,
        },
        metrics={
            "current_price": insight.metrics.current_price,
            "sma_50": insight.metrics.sma_50,
            "sma_200": insight.metrics.sma_200,
            "parabolic_sar": insight.metrics.parabolic_sar,
            "pe_ratio": insight.metrics.pe_ratio,
            "revenue_growth": insight.metrics.revenue_growth,
            "profit_margin": insight.metrics.profit_margin,
            "debt_to_equity": insight.metrics.debt_to_equity,
            "annualized_volatility": insight.metrics.annualized_volatility,
            "max_drawdown": insight.metrics.max_drawdown,
            "benchmark_ticker": insight.metrics.benchmark_ticker,
            "benchmark_above_sma200": insight.metrics.benchmark_above_sma200,
        },
        horizon=insight.horizon.value,
        scenario=insight.scenario,
        risks=insight.risks,
        explanation=insight.explanation,
        portfolio_role=insight.portfolio_role.value if insight.portfolio_role else None,
        health_score=insight.scores.health_score if insight.scores else None,
        profile_fit_score=insight.scores.profile_fit_score if insight.scores else None,
        alternatives=alternatives_json,
        position_context=position_json,
        news_flags=news_json,
    )


def save_insights(
    session: AsyncSession, portfolio_id: int, insights: list[Insight]
) -> None:
    """Append insights to a portfolio's history (never deletes prior rows)."""
    for insight in insights:
        record = insight_to_record(insight)
        record.portfolio_id = portfolio_id
        session.add(record)
