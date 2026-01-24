from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import Trend
from insight_engine.rules.trend_rules import evaluate_trend


def test_bullish_trend():
    metrics = MetricsSummary(current_price=160.0, sma_50=150.0, sma_200=140.0)
    assert evaluate_trend(metrics) == Trend.bullish


def test_bearish_trend():
    metrics = MetricsSummary(current_price=120.0, sma_50=130.0, sma_200=140.0)
    assert evaluate_trend(metrics) == Trend.bearish


def test_sideways_trend_mixed():
    # Price above SMA200 but below SMA50
    metrics = MetricsSummary(current_price=145.0, sma_50=150.0, sma_200=140.0)
    assert evaluate_trend(metrics) == Trend.sideways


def test_sideways_trend_sma_crossed():
    # SMA50 below SMA200 but price above both
    metrics = MetricsSummary(current_price=160.0, sma_50=135.0, sma_200=140.0)
    assert evaluate_trend(metrics) == Trend.sideways


def test_sideways_when_missing_data():
    metrics = MetricsSummary(current_price=100.0, sma_50=None, sma_200=None)
    assert evaluate_trend(metrics) == Trend.sideways


def test_sideways_when_no_price():
    metrics = MetricsSummary(current_price=None, sma_50=150.0, sma_200=140.0)
    assert evaluate_trend(metrics) == Trend.sideways


# --- SAR-augmented trend tests ---


def test_bullish_confirmed_by_sar():
    """Bullish SMA trend confirmed by SAR (price > SAR)."""
    metrics = MetricsSummary(
        current_price=160.0, sma_50=150.0, sma_200=140.0, parabolic_sar=145.0
    )
    assert evaluate_trend(metrics) == Trend.bullish


def test_bullish_contradicted_by_sar():
    """Bullish SMA trend contradicted by SAR (price < SAR) → sideways."""
    metrics = MetricsSummary(
        current_price=160.0, sma_50=150.0, sma_200=140.0, parabolic_sar=170.0
    )
    assert evaluate_trend(metrics) == Trend.sideways


def test_bearish_confirmed_by_sar():
    """Bearish SMA trend confirmed by SAR (price < SAR)."""
    metrics = MetricsSummary(
        current_price=120.0, sma_50=130.0, sma_200=140.0, parabolic_sar=135.0
    )
    assert evaluate_trend(metrics) == Trend.bearish


def test_bearish_contradicted_by_sar():
    """Bearish SMA trend contradicted by SAR (price > SAR) → sideways."""
    metrics = MetricsSummary(
        current_price=120.0, sma_50=130.0, sma_200=140.0, parabolic_sar=110.0
    )
    assert evaluate_trend(metrics) == Trend.sideways


def test_sideways_sma_sar_bullish():
    """Sideways SMA but SAR is bullish → bullish."""
    metrics = MetricsSummary(
        current_price=145.0, sma_50=150.0, sma_200=140.0, parabolic_sar=130.0
    )
    assert evaluate_trend(metrics) == Trend.bullish


def test_sideways_sma_sar_bearish():
    """Sideways SMA but SAR is bearish → bearish."""
    metrics = MetricsSummary(
        current_price=145.0, sma_50=150.0, sma_200=140.0, parabolic_sar=160.0
    )
    assert evaluate_trend(metrics) == Trend.bearish


def test_sar_none_preserves_sma_trend():
    """When SAR is None, behavior is backwards-compatible with SMA-only logic."""
    metrics = MetricsSummary(
        current_price=160.0, sma_50=150.0, sma_200=140.0, parabolic_sar=None
    )
    assert evaluate_trend(metrics) == Trend.bullish
