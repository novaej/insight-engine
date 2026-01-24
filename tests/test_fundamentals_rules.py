from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import Fundamentals
from insight_engine.rules.fundamentals_rules import evaluate_fundamentals


def test_strong_fundamentals():
    metrics = MetricsSummary(
        revenue_growth=0.15,
        profit_margin=0.20,
        debt_to_equity=0.5,
    )
    assert evaluate_fundamentals(metrics) == Fundamentals.strong


def test_weak_fundamentals():
    metrics = MetricsSummary(
        revenue_growth=-0.05,
        profit_margin=0.05,
        debt_to_equity=2.0,
    )
    assert evaluate_fundamentals(metrics) == Fundamentals.weak


def test_mixed_fundamentals_one_positive():
    metrics = MetricsSummary(
        revenue_growth=0.15,  # positive
        profit_margin=0.05,   # negative
        debt_to_equity=2.0,   # negative
    )
    assert evaluate_fundamentals(metrics) == Fundamentals.mixed


def test_mixed_fundamentals_two_positive():
    metrics = MetricsSummary(
        revenue_growth=0.15,  # positive
        profit_margin=0.20,   # positive
        debt_to_equity=2.0,   # negative
    )
    assert evaluate_fundamentals(metrics) == Fundamentals.mixed


def test_mixed_when_no_data():
    metrics = MetricsSummary(
        revenue_growth=None,
        profit_margin=None,
        debt_to_equity=None,
    )
    assert evaluate_fundamentals(metrics) == Fundamentals.mixed


def test_partial_data_strong():
    # Only margin available and it's good
    metrics = MetricsSummary(
        revenue_growth=None,
        profit_margin=0.25,
        debt_to_equity=None,
    )
    assert evaluate_fundamentals(metrics) == Fundamentals.mixed  # only 1 data point, score=1


def test_boundary_values():
    # Exactly at thresholds
    metrics = MetricsSummary(
        revenue_growth=0.10,   # not > 0.10
        profit_margin=0.15,    # not > 0.15
        debt_to_equity=1.0,    # not < 1.0
    )
    assert evaluate_fundamentals(metrics) == Fundamentals.weak
