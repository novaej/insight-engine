from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import Valuation
from insight_engine.rules.valuation_rules import evaluate_valuation


def test_cheap_valuation():
    # P/E = 14, historical avg = 20 -> ratio = 0.7 < 0.8
    metrics = MetricsSummary(pe_ratio=14.0, pe_historical_avg=20.0)
    assert evaluate_valuation(metrics) == Valuation.cheap


def test_expensive_valuation():
    # P/E = 30, historical avg = 20 -> ratio = 1.5 > 1.2
    metrics = MetricsSummary(pe_ratio=30.0, pe_historical_avg=20.0)
    assert evaluate_valuation(metrics) == Valuation.expensive


def test_reasonable_valuation():
    # P/E = 20, historical avg = 20 -> ratio = 1.0
    metrics = MetricsSummary(pe_ratio=20.0, pe_historical_avg=20.0)
    assert evaluate_valuation(metrics) == Valuation.reasonable


def test_reasonable_valuation_at_boundary():
    # P/E = 16, historical avg = 20 -> ratio = 0.8 (boundary)
    metrics = MetricsSummary(pe_ratio=16.0, pe_historical_avg=20.0)
    assert evaluate_valuation(metrics) == Valuation.reasonable


def test_inconclusive_no_pe():
    metrics = MetricsSummary(pe_ratio=None, pe_historical_avg=20.0)
    assert evaluate_valuation(metrics) == Valuation.inconclusive


def test_inconclusive_no_historical():
    metrics = MetricsSummary(pe_ratio=20.0, pe_historical_avg=None)
    assert evaluate_valuation(metrics) == Valuation.inconclusive


def test_inconclusive_zero_historical():
    metrics = MetricsSummary(pe_ratio=20.0, pe_historical_avg=0.0)
    assert evaluate_valuation(metrics) == Valuation.inconclusive
