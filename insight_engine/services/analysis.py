from insight_engine.domain.entities import DimensionResults, Insight, MetricsSummary, UserProfile
from insight_engine.rules.fundamentals_rules import evaluate_fundamentals
from insight_engine.rules.horizon_rules import determine_horizon
from insight_engine.rules.market_context_rules import evaluate_market_context
from insight_engine.rules.risk_rules import evaluate_risk
from insight_engine.rules.synthesis import synthesize_state
from insight_engine.rules.trend_rules import evaluate_trend
from insight_engine.rules.valuation_rules import evaluate_valuation
from insight_engine.services.data_provider import (
    fetch_sp500_data,
    fetch_ticker_data,
    fetch_ticker_info,
)
from insight_engine.services.metrics import calculate_metrics


def analyze_asset(ticker: str, user_profile: UserProfile | None = None) -> Insight:
    """Run the full analysis pipeline for a single asset."""
    hist = fetch_ticker_data(ticker)
    info = fetch_ticker_info(ticker)
    sp500_hist = fetch_sp500_data()

    metrics = calculate_metrics(hist, info, sp500_hist)
    dimensions = evaluate_dimensions(metrics)
    asset_state = synthesize_state(dimensions)
    horizon = determine_horizon(asset_state, dimensions, user_profile)

    return Insight(
        ticker=ticker.upper(),
        asset_state=asset_state,
        dimensions=dimensions,
        metrics=metrics,
        horizon=horizon,
    )


def evaluate_dimensions(metrics: MetricsSummary) -> DimensionResults:
    """Evaluate all five dimensions from metrics."""
    return DimensionResults(
        trend=evaluate_trend(metrics),
        valuation=evaluate_valuation(metrics),
        fundamentals=evaluate_fundamentals(metrics),
        risk_level=evaluate_risk(metrics),
        market_context=evaluate_market_context(metrics),
    )


def derive_risks(dimensions: DimensionResults, metrics: MetricsSummary) -> list[str]:
    """Derive up to 3 risk factors from dimension results."""
    risks = []
    from insight_engine.domain.enums import (
        Fundamentals,
        MarketContext,
        RiskLevel,
        Trend,
        Valuation,
    )

    if dimensions.valuation == Valuation.expensive:
        risks.append("High valuation relative to historical average")
    if dimensions.risk_level == RiskLevel.high:
        risks.append("Elevated volatility and drawdown risk")
    if dimensions.market_context == MarketContext.adverse:
        risks.append("Adverse broad market environment")
    if dimensions.trend == Trend.bearish:
        risks.append("Bearish price trend")
    if dimensions.fundamentals == Fundamentals.weak:
        risks.append("Weak business fundamentals")

    return risks[:3]
