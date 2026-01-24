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
