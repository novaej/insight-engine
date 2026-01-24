from insight_engine.domain.entities import DimensionResults, MetricsSummary, UserProfile
from insight_engine.domain.enums import (
    Fundamentals,
    RiskLevel,
    Trend,
    Valuation,
)


def compute_health_score(dimensions: DimensionResults, metrics: MetricsSummary) -> int:
    """Compute a 0-100 health score from dimensions and metrics."""
    score = 0

    # Trend (0-25)
    trend_map = {Trend.bullish: 25, Trend.sideways: 15, Trend.bearish: 0}
    score += trend_map.get(dimensions.trend, 0)

    # Fundamentals (0-25)
    fund_map = {Fundamentals.strong: 25, Fundamentals.mixed: 15, Fundamentals.weak: 0}
    score += fund_map.get(dimensions.fundamentals, 0)

    # Valuation (0-20)
    val_map = {
        Valuation.cheap: 20,
        Valuation.reasonable: 15,
        Valuation.expensive: 5,
        Valuation.inconclusive: 10,
    }
    score += val_map.get(dimensions.valuation, 10)

    # Risk (0-15)
    risk_map = {RiskLevel.low: 15, RiskLevel.medium: 10, RiskLevel.high: 0}
    score += risk_map.get(dimensions.risk_level, 0)

    # Debt penalty
    if metrics.debt_to_equity is not None and metrics.debt_to_equity > 2.0:
        score = max(0, score - 5)

    # Drawdown (0-15)
    dd = metrics.max_drawdown
    if dd is not None:
        if dd > -0.15:
            score += 15
        elif dd > -0.30:
            score += 8

    return max(0, min(100, score))


def compute_profile_fit_score(
    metrics: MetricsSummary,
    dimensions: DimensionResults,
    user_profile: UserProfile,
) -> int:
    """Compute a 0-100 profile fit score based on risk tolerance alignment."""
    score = 0
    risk = user_profile.risk.value  # low, moderate, high

    # Volatility alignment (0-40)
    vol = metrics.annualized_volatility
    if vol is not None:
        vol_pct = vol * 100
        thresholds = {"low": 15, "moderate": 25, "high": 40}
        limit = thresholds.get(risk, 25)
        if vol_pct <= limit:
            score += 40
        elif vol_pct <= limit * 1.5:
            score += 20
        # else 0

    # Drawdown alignment (0-30)
    dd = metrics.max_drawdown
    if dd is not None:
        dd_thresholds = {"low": -0.10, "moderate": -0.20, "high": -0.35}
        limit = dd_thresholds.get(risk, -0.20)
        if dd >= limit:
            score += 30
        elif dd >= limit * 1.5:
            score += 15
        # else 0

    # Horizon alignment (0-30)
    horizon_input = user_profile.horizon.lower()
    from insight_engine.domain.enums import Horizon
    from insight_engine.rules.horizon_rules import determine_horizon
    from insight_engine.rules.synthesis import synthesize_state

    asset_state = synthesize_state(dimensions)
    asset_horizon = determine_horizon(asset_state, dimensions, user_profile)

    horizon_order = {
        Horizon.short_term: 0,
        Horizon.medium_term: 1,
        Horizon.long_term: 2,
        Horizon.not_recommended: -1,
    }
    user_order_map = {"short": 0, "medium": 1, "long": 2}
    user_order = user_order_map.get(horizon_input, 1)
    asset_order = horizon_order.get(asset_horizon, 1)

    if asset_order == -1:
        score += 0
    elif abs(asset_order - user_order) == 0:
        score += 30
    elif abs(asset_order - user_order) == 1:
        score += 15
    # else 0

    return max(0, min(100, score))
