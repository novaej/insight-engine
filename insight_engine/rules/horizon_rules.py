from insight_engine.domain.entities import DimensionResults, UserProfile
from insight_engine.domain.enums import AssetState, Horizon, RiskLevel, Trend


def determine_horizon(
    asset_state: AssetState,
    dimensions: DimensionResults,
    user_profile: UserProfile | None = None,
) -> Horizon:
    """Determine the recommended horizon for an asset.

    Logic:
    - Unattractive -> not_recommended
    - Risky -> short_term (if at all)
    - Healthy + bullish trend + low/medium risk -> long_term
    - Healthy_but_expensive -> medium_term (caution on valuation)
    - Neutral -> medium_term
    """
    if asset_state == AssetState.unattractive:
        return Horizon.not_recommended

    if asset_state == AssetState.risky:
        return Horizon.short_term

    if asset_state == AssetState.healthy:
        if dimensions.trend == Trend.bullish and dimensions.risk_level in (
            RiskLevel.low,
            RiskLevel.medium,
        ):
            return Horizon.long_term
        return Horizon.medium_term

    if asset_state == AssetState.healthy_but_expensive:
        return Horizon.medium_term

    # neutral
    return Horizon.medium_term
