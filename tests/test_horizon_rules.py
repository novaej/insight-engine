from insight_engine.domain.entities import DimensionResults
from insight_engine.domain.enums import (
    AssetState,
    Fundamentals,
    Horizon,
    MarketContext,
    RiskLevel,
    Trend,
    Valuation,
)
from insight_engine.rules.horizon_rules import determine_horizon


def test_unattractive_not_recommended():
    dims = DimensionResults(
        trend=Trend.bearish,
        valuation=Valuation.expensive,
        fundamentals=Fundamentals.weak,
        risk_level=RiskLevel.high,
        market_context=MarketContext.adverse,
    )
    assert determine_horizon(AssetState.unattractive, dims) == Horizon.not_recommended


def test_risky_short_term():
    dims = DimensionResults(
        trend=Trend.bearish,
        valuation=Valuation.reasonable,
        fundamentals=Fundamentals.weak,
        risk_level=RiskLevel.medium,
        market_context=MarketContext.favorable,
    )
    assert determine_horizon(AssetState.risky, dims) == Horizon.short_term


def test_healthy_bullish_low_risk_long_term():
    dims = DimensionResults(
        trend=Trend.bullish,
        valuation=Valuation.reasonable,
        fundamentals=Fundamentals.strong,
        risk_level=RiskLevel.low,
        market_context=MarketContext.favorable,
    )
    assert determine_horizon(AssetState.healthy, dims) == Horizon.long_term


def test_healthy_but_expensive_medium_term():
    dims = DimensionResults(
        trend=Trend.bullish,
        valuation=Valuation.expensive,
        fundamentals=Fundamentals.strong,
        risk_level=RiskLevel.low,
        market_context=MarketContext.favorable,
    )
    assert determine_horizon(AssetState.healthy_but_expensive, dims) == Horizon.medium_term


def test_neutral_medium_term():
    dims = DimensionResults(
        trend=Trend.sideways,
        valuation=Valuation.reasonable,
        fundamentals=Fundamentals.mixed,
        risk_level=RiskLevel.medium,
        market_context=MarketContext.favorable,
    )
    assert determine_horizon(AssetState.neutral, dims) == Horizon.medium_term


def test_healthy_high_risk_medium_term():
    dims = DimensionResults(
        trend=Trend.bullish,
        valuation=Valuation.reasonable,
        fundamentals=Fundamentals.strong,
        risk_level=RiskLevel.high,
        market_context=MarketContext.favorable,
    )
    assert determine_horizon(AssetState.healthy, dims) == Horizon.medium_term
