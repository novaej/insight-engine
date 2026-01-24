from insight_engine.domain.entities import DimensionResults
from insight_engine.domain.enums import (
    AssetState,
    Fundamentals,
    MarketContext,
    RiskLevel,
    Trend,
    Valuation,
)
from insight_engine.rules.synthesis import synthesize_state


def test_healthy_state():
    dims = DimensionResults(
        trend=Trend.bullish,
        valuation=Valuation.reasonable,
        fundamentals=Fundamentals.strong,
        risk_level=RiskLevel.low,
        market_context=MarketContext.favorable,
    )
    assert synthesize_state(dims) == AssetState.healthy


def test_healthy_with_cheap_valuation():
    dims = DimensionResults(
        trend=Trend.bullish,
        valuation=Valuation.cheap,
        fundamentals=Fundamentals.strong,
        risk_level=RiskLevel.low,
        market_context=MarketContext.favorable,
    )
    assert synthesize_state(dims) == AssetState.healthy


def test_healthy_but_expensive():
    dims = DimensionResults(
        trend=Trend.bullish,
        valuation=Valuation.expensive,
        fundamentals=Fundamentals.strong,
        risk_level=RiskLevel.low,
        market_context=MarketContext.favorable,
    )
    assert synthesize_state(dims) == AssetState.healthy_but_expensive


def test_risky_weak_fundamentals():
    dims = DimensionResults(
        trend=Trend.bullish,
        valuation=Valuation.cheap,
        fundamentals=Fundamentals.weak,
        risk_level=RiskLevel.low,
        market_context=MarketContext.favorable,
    )
    assert synthesize_state(dims) == AssetState.risky


def test_unattractive_high_risk_adverse():
    dims = DimensionResults(
        trend=Trend.sideways,
        valuation=Valuation.reasonable,
        fundamentals=Fundamentals.mixed,
        risk_level=RiskLevel.high,
        market_context=MarketContext.adverse,
    )
    assert synthesize_state(dims) == AssetState.unattractive


def test_neutral_sideways_mixed():
    dims = DimensionResults(
        trend=Trend.sideways,
        valuation=Valuation.reasonable,
        fundamentals=Fundamentals.mixed,
        risk_level=RiskLevel.medium,
        market_context=MarketContext.favorable,
    )
    assert synthesize_state(dims) == AssetState.neutral


def test_two_negatives_cannot_be_healthy():
    # Bearish + expensive = 2 negatives
    dims = DimensionResults(
        trend=Trend.bearish,
        valuation=Valuation.expensive,
        fundamentals=Fundamentals.strong,
        risk_level=RiskLevel.low,
        market_context=MarketContext.favorable,
    )
    assert synthesize_state(dims) in (AssetState.risky, AssetState.neutral, AssetState.unattractive)


def test_two_negatives_with_high_risk():
    dims = DimensionResults(
        trend=Trend.bearish,
        valuation=Valuation.expensive,
        fundamentals=Fundamentals.mixed,
        risk_level=RiskLevel.high,
        market_context=MarketContext.favorable,
    )
    assert synthesize_state(dims) == AssetState.unattractive


def test_neutral_inconclusive_valuation():
    dims = DimensionResults(
        trend=Trend.sideways,
        valuation=Valuation.inconclusive,
        fundamentals=Fundamentals.mixed,
        risk_level=RiskLevel.medium,
        market_context=MarketContext.favorable,
    )
    assert synthesize_state(dims) == AssetState.neutral


def test_all_negative():
    dims = DimensionResults(
        trend=Trend.bearish,
        valuation=Valuation.expensive,
        fundamentals=Fundamentals.weak,
        risk_level=RiskLevel.high,
        market_context=MarketContext.adverse,
    )
    # Weak fundamentals takes priority -> risky
    assert synthesize_state(dims) == AssetState.risky
