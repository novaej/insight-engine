from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import MarketContext
from insight_engine.rules.market_context_rules import evaluate_market_context


def test_favorable_context():
    metrics = MetricsSummary(sp500_above_sma200=True)
    assert evaluate_market_context(metrics) == MarketContext.favorable


def test_adverse_context():
    metrics = MetricsSummary(sp500_above_sma200=False)
    assert evaluate_market_context(metrics) == MarketContext.adverse


def test_default_favorable_when_no_data():
    metrics = MetricsSummary(sp500_above_sma200=None)
    assert evaluate_market_context(metrics) == MarketContext.favorable
