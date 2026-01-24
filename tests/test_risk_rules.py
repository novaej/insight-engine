from insight_engine.domain.entities import MetricsSummary
from insight_engine.domain.enums import RiskLevel
from insight_engine.rules.risk_rules import evaluate_risk


def test_high_risk_high_volatility():
    metrics = MetricsSummary(annualized_volatility=0.50, max_drawdown=-0.20)
    assert evaluate_risk(metrics) == RiskLevel.high


def test_high_risk_severe_drawdown():
    metrics = MetricsSummary(annualized_volatility=0.25, max_drawdown=-0.35)
    assert evaluate_risk(metrics) == RiskLevel.high


def test_low_risk():
    metrics = MetricsSummary(annualized_volatility=0.15, max_drawdown=-0.10)
    assert evaluate_risk(metrics) == RiskLevel.low


def test_medium_risk():
    metrics = MetricsSummary(annualized_volatility=0.25, max_drawdown=-0.20)
    assert evaluate_risk(metrics) == RiskLevel.medium


def test_medium_risk_low_vol_but_bad_drawdown():
    # Low volatility but drawdown too severe for "low"
    metrics = MetricsSummary(annualized_volatility=0.15, max_drawdown=-0.20)
    assert evaluate_risk(metrics) == RiskLevel.medium


def test_medium_when_no_data():
    metrics = MetricsSummary(annualized_volatility=None, max_drawdown=None)
    assert evaluate_risk(metrics) == RiskLevel.medium


def test_high_risk_both_bad():
    metrics = MetricsSummary(annualized_volatility=0.50, max_drawdown=-0.40)
    assert evaluate_risk(metrics) == RiskLevel.high
