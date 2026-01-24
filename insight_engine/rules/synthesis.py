from insight_engine.domain.entities import DimensionResults
from insight_engine.domain.enums import (
    AssetState,
    Fundamentals,
    MarketContext,
    RiskLevel,
    Trend,
    Valuation,
)


def synthesize_state(dimensions: DimensionResults) -> AssetState:
    """Synthesize the final asset state from the five dimension results.

    Rules (applied in priority order):
    1. Weak fundamentals -> risky
    2. High risk + adverse context -> unattractive
    3. Count negative signals; 2+ negatives -> cannot be healthy
    4. Bullish + (reasonable or cheap) + strong fundamentals -> healthy
    5. Would-be healthy + expensive valuation -> healthy_but_expensive
    6. Default -> neutral
    """
    # Rule 1: Weak fundamentals always means risky
    if dimensions.fundamentals == Fundamentals.weak:
        return AssetState.risky

    # Rule 2: High risk + adverse context -> unattractive
    high_risk = dimensions.risk_level == RiskLevel.high
    adverse = dimensions.market_context == MarketContext.adverse
    if high_risk and adverse:
        return AssetState.unattractive

    # Count negative signals
    negative_count = _count_negatives(dimensions)

    # Rule 3: 2+ negatives cannot be healthy
    if negative_count >= 2:
        if high_risk or adverse:
            return AssetState.unattractive
        return AssetState.risky

    # Rule 4: Bullish + reasonable/cheap + strong -> healthy
    is_bullish = dimensions.trend == Trend.bullish
    is_valued_well = dimensions.valuation in (Valuation.cheap, Valuation.reasonable)
    is_strong = dimensions.fundamentals == Fundamentals.strong

    if is_bullish and is_valued_well and is_strong:
        return AssetState.healthy

    # Rule 5: Would-be healthy but expensive
    if is_bullish and is_strong and dimensions.valuation == Valuation.expensive:
        return AssetState.healthy_but_expensive

    # Default
    return AssetState.neutral


def _count_negatives(dimensions: DimensionResults) -> int:
    """Count the number of negative dimension signals."""
    count = 0
    if dimensions.trend == Trend.bearish:
        count += 1
    if dimensions.valuation == Valuation.expensive:
        count += 1
    if dimensions.fundamentals == Fundamentals.weak:
        count += 1
    if dimensions.risk_level == RiskLevel.high:
        count += 1
    if dimensions.market_context == MarketContext.adverse:
        count += 1
    return count
