"""Position-aware portfolio rules: weights, concentration, weighted risk.

Pure functions over already-computed insights — no I/O, no AI. Like all rules,
they classify states; they do not give orders.
"""

from insight_engine.domain.entities import ConcentrationResult, Insight, PositionContext
from insight_engine.domain.enums import AssetState, ConcentrationState, RiskLevel

POSITION_WEIGHT_LIMIT = 0.25
ROLE_WEIGHT_LIMIT = 0.40

_NEGATIVE_STATES = (AssetState.risky, AssetState.unattractive)


def compute_position_contexts(assets, insights: list[Insight]) -> float | None:
    """Attach a PositionContext to each insight and return total portfolio value.

    `assets` are per-ticker aggregates (quantity, weighted-average purchase
    price). Positions without a current price get no market value or weight and
    are excluded from the total.
    """
    by_ticker = {a.ticker.upper(): a for a in assets}

    total_value = 0.0
    for insight in insights:
        asset = by_ticker.get(insight.ticker.upper())
        if asset is None:
            continue
        price = insight.metrics.current_price
        market_value = asset.quantity * price if price is not None else None
        if market_value is not None:
            total_value += market_value

        unrealized = None
        if price is not None and asset.purchase_price:
            unrealized = (price - asset.purchase_price) / asset.purchase_price

        insight.position = PositionContext(
            quantity=asset.quantity,
            market_value=market_value,
            avg_purchase_price=asset.purchase_price,
            unrealized_gain_pct=unrealized,
        )

    if total_value <= 0:
        return None

    for insight in insights:
        if insight.position and insight.position.market_value is not None:
            insight.position.weight = insight.position.market_value / total_value

    return total_value


def evaluate_concentration(insights: list[Insight]) -> ConcentrationResult:
    """Flag positions over 25% of value and roles over 40% combined."""
    flagged_tickers = [
        i.ticker
        for i in insights
        if i.position and i.position.weight is not None
        and i.position.weight > POSITION_WEIGHT_LIMIT
    ]

    role_weights: dict[str, float] = {}
    for insight in insights:
        if insight.portfolio_role and insight.position and insight.position.weight:
            role = insight.portfolio_role.value
            role_weights[role] = role_weights.get(role, 0.0) + insight.position.weight
    flagged_roles = [
        role for role, weight in sorted(role_weights.items()) if weight > ROLE_WEIGHT_LIMIT
    ]

    state = (
        ConcentrationState.concentrated
        if flagged_tickers or flagged_roles
        else ConcentrationState.diversified
    )
    return ConcentrationResult(
        state=state, flagged_tickers=flagged_tickers, flagged_roles=flagged_roles
    )


def determine_weighted_risk(insights: list[Insight]) -> RiskLevel:
    """Portfolio risk weighted by position value.

    Falls back to count-based logic when no weights are available (e.g. prices
    missing for every position).
    """
    weights = [
        (i, i.position.weight)
        for i in insights
        if i.position and i.position.weight is not None
    ]
    if not weights:
        return _count_based_risk(insights)

    risky_weight = sum(w for i, w in weights if i.asset_state in _NEGATIVE_STATES)
    if risky_weight > 0.5:
        return RiskLevel.high
    elif risky_weight > 0:
        return RiskLevel.medium
    return RiskLevel.low


def _count_based_risk(insights: list[Insight]) -> RiskLevel:
    high_risk_count = sum(1 for i in insights if i.asset_state in _NEGATIVE_STATES)
    if high_risk_count > len(insights) / 2:
        return RiskLevel.high
    elif high_risk_count > 0:
        return RiskLevel.medium
    return RiskLevel.low
