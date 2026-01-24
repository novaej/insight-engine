import pytest

from insight_engine.domain.entities import DimensionResults, MetricsSummary, UserProfile
from insight_engine.domain.enums import (
    Fundamentals,
    InvestmentObjective,
    MarketContext,
    RiskLevel,
    RiskProfile,
    Trend,
    Valuation,
)
from insight_engine.rules.scoring_rules import compute_health_score, compute_profile_fit_score


class TestHealthScore:
    def test_all_positive_high_score(self):
        dims = DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.cheap,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        )
        metrics = MetricsSummary(
            max_drawdown=-0.05,
            debt_to_equity=0.5,
        )
        score = compute_health_score(dims, metrics)
        # 25 + 20 + 25 + 15 + 15 = 100
        assert score == 100

    def test_all_negative_low_score(self):
        dims = DimensionResults(
            trend=Trend.bearish,
            valuation=Valuation.expensive,
            fundamentals=Fundamentals.weak,
            risk_level=RiskLevel.high,
            market_context=MarketContext.adverse,
        )
        metrics = MetricsSummary(
            max_drawdown=-0.50,
            debt_to_equity=3.0,
        )
        score = compute_health_score(dims, metrics)
        # 0 + 5 + 0 + 0 + 0 - 5(debt penalty) = 0 (clamped)
        assert score == 0

    def test_mixed_dimensions(self):
        dims = DimensionResults(
            trend=Trend.sideways,
            valuation=Valuation.reasonable,
            fundamentals=Fundamentals.mixed,
            risk_level=RiskLevel.medium,
            market_context=MarketContext.favorable,
        )
        metrics = MetricsSummary(
            max_drawdown=-0.20,
            debt_to_equity=1.0,
        )
        score = compute_health_score(dims, metrics)
        # 15 + 15 + 15 + 10 + 8 = 63
        assert score == 63

    def test_high_debt_penalty(self):
        dims = DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.cheap,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        )
        metrics = MetricsSummary(
            max_drawdown=-0.05,
            debt_to_equity=2.5,
        )
        score = compute_health_score(dims, metrics)
        # 25 + 20 + 25 + 15 + 15 - 5 = 95
        assert score == 95

    def test_none_metrics_handled(self):
        dims = DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.reasonable,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        )
        metrics = MetricsSummary()  # All None
        score = compute_health_score(dims, metrics)
        # 25 + 15 + 25 + 15 + 0(no drawdown) = 80
        assert score == 80

    def test_inconclusive_valuation(self):
        dims = DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.inconclusive,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        )
        metrics = MetricsSummary(max_drawdown=-0.05)
        score = compute_health_score(dims, metrics)
        # 25 + 10 + 25 + 15 + 15 = 90
        assert score == 90


class TestProfileFitScore:
    def test_perfect_fit_low_risk_short_horizon(self):
        metrics = MetricsSummary(
            annualized_volatility=0.10,
            max_drawdown=-0.05,
        )
        dims = DimensionResults(
            trend=Trend.bearish,
            valuation=Valuation.expensive,
            fundamentals=Fundamentals.weak,
            risk_level=RiskLevel.high,
            market_context=MarketContext.adverse,
        )
        profile = UserProfile(
            risk=RiskProfile.low,
            horizon="short",
            objective=InvestmentObjective.capital_protection,
        )
        score = compute_profile_fit_score(metrics, dims, profile)
        # vol 10% <= 15% → 40
        # dd -5% >= -10% → 30
        # asset: weak fundamentals → risky → short_term, user short → match → 30
        assert score == 100

    def test_volatility_mismatch(self):
        metrics = MetricsSummary(
            annualized_volatility=0.50,
            max_drawdown=-0.05,
        )
        dims = DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.reasonable,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        )
        profile = UserProfile(
            risk=RiskProfile.low,
            horizon="long",
            objective=InvestmentObjective.growth,
        )
        score = compute_profile_fit_score(metrics, dims, profile)
        # vol 50% > 15% and > 22.5% → 0
        # dd -5% >= -10% → 30
        # asset: healthy + bullish + low risk → long_term, user long → match → 30
        assert score == 60

    def test_high_risk_profile_tolerates_more(self):
        metrics = MetricsSummary(
            annualized_volatility=0.35,
            max_drawdown=-0.30,
        )
        dims = DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.reasonable,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        )
        profile = UserProfile(
            risk=RiskProfile.high,
            horizon="long",
            objective=InvestmentObjective.growth,
        )
        score = compute_profile_fit_score(metrics, dims, profile)
        # vol 35% <= 40% → 40
        # dd -30% >= -35% → 30
        # horizon match: long → long → 30
        assert score == 100

    def test_none_metrics(self):
        metrics = MetricsSummary()
        dims = DimensionResults(
            trend=Trend.sideways,
            valuation=Valuation.reasonable,
            fundamentals=Fundamentals.mixed,
            risk_level=RiskLevel.medium,
            market_context=MarketContext.favorable,
        )
        profile = UserProfile(
            risk=RiskProfile.moderate,
            horizon="medium",
            objective=InvestmentObjective.growth,
        )
        score = compute_profile_fit_score(metrics, dims, profile)
        # vol None → 0
        # dd None → 0
        # horizon: neutral → medium_term, user medium → match → 30
        assert score == 30

    def test_horizon_adjacent_partial_score(self):
        metrics = MetricsSummary(
            annualized_volatility=0.20,
            max_drawdown=-0.15,
        )
        dims = DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.reasonable,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        )
        profile = UserProfile(
            risk=RiskProfile.moderate,
            horizon="medium",
            objective=InvestmentObjective.growth,
        )
        score = compute_profile_fit_score(metrics, dims, profile)
        # vol 20% <= 25% → 40
        # dd -15% >= -20% → 30
        # asset: healthy + bullish + low → long_term (order 2), user medium (order 1) → adjacent → 15
        assert score == 85
