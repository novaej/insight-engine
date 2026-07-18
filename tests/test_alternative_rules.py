import pytest

from insight_engine.domain.entities import AssetScores, NewsFlags, UserProfile
from insight_engine.domain.enums import InvestmentObjective, RiskProfile
from insight_engine.rules.alternative_rules import filter_and_rank_candidates, should_trigger_alternatives


class TestShouldTriggerAlternatives:
    def test_low_health_score_triggers(self):
        scores = AssetScores(health_score=30, profile_fit_score=70)
        triggered, reasons = should_trigger_alternatives(scores)
        assert triggered is True
        assert any("health score" in r.lower() for r in reasons)

    def test_low_profile_fit_triggers(self):
        scores = AssetScores(health_score=70, profile_fit_score=30)
        triggered, reasons = should_trigger_alternatives(scores)
        assert triggered is True
        assert any("profile fit" in r.lower() for r in reasons)

    def test_both_low_triggers(self):
        scores = AssetScores(health_score=40, profile_fit_score=40)
        triggered, reasons = should_trigger_alternatives(scores)
        assert triggered is True
        assert len(reasons) == 2

    def test_high_scores_no_trigger(self):
        scores = AssetScores(health_score=70, profile_fit_score=70)
        triggered, reasons = should_trigger_alternatives(scores)
        assert triggered is False
        assert reasons == []

    def test_boundary_50_no_trigger(self):
        scores = AssetScores(health_score=50, profile_fit_score=50)
        triggered, reasons = should_trigger_alternatives(scores)
        assert triggered is False

    def test_news_regulatory_risk_triggers(self):
        scores = AssetScores(health_score=80, profile_fit_score=80)
        news_flags = NewsFlags(regulatory_risk=True)
        triggered, reasons = should_trigger_alternatives(scores, news_flags)
        assert triggered is True
        assert any("regulatory" in r.lower() for r in reasons)

    def test_news_earnings_negative_triggers(self):
        scores = AssetScores(health_score=80, profile_fit_score=80)
        news_flags = NewsFlags(earnings_negative=True)
        triggered, reasons = should_trigger_alternatives(scores, news_flags)
        assert triggered is True
        assert any("earnings" in r.lower() for r in reasons)

    def test_news_management_change_triggers(self):
        scores = AssetScores(health_score=80, profile_fit_score=80)
        news_flags = NewsFlags(management_change=True)
        triggered, reasons = should_trigger_alternatives(scores, news_flags)
        assert triggered is True

    def test_news_litigation_risk_triggers(self):
        scores = AssetScores(health_score=80, profile_fit_score=80)
        news_flags = NewsFlags(litigation_risk=True)
        triggered, reasons = should_trigger_alternatives(scores, news_flags)
        assert triggered is True

    def test_multiple_news_flags(self):
        scores = AssetScores(health_score=80, profile_fit_score=80)
        news_flags = NewsFlags(regulatory_risk=True, litigation_risk=True)
        triggered, reasons = should_trigger_alternatives(scores, news_flags)
        assert triggered is True
        assert len(reasons) == 2

    def test_no_news_flags_no_trigger(self):
        scores = AssetScores(health_score=80, profile_fit_score=80)
        news_flags = NewsFlags()
        triggered, reasons = should_trigger_alternatives(scores, news_flags)
        assert triggered is False


class TestFilterAndRankCandidates:
    @pytest.fixture
    def low_risk_profile(self):
        return UserProfile(
            risk=RiskProfile.low,
            horizon="long",
            objective=InvestmentObjective.capital_protection,
        )

    @pytest.fixture
    def high_risk_profile(self):
        return UserProfile(
            risk=RiskProfile.high,
            horizon="long",
            objective=InvestmentObjective.growth,
        )

    def test_filters_high_volatility_for_low_risk(self, low_risk_profile):
        candidates = [
            {"ticker": "AAA", "health_score": 90, "annualized_volatility": 0.10, "max_drawdown": -0.05},
            {"ticker": "BBB", "health_score": 95, "annualized_volatility": 0.30, "max_drawdown": -0.05},
        ]
        result = filter_and_rank_candidates(candidates, low_risk_profile)
        assert len(result) == 1
        assert result[0]["ticker"] == "AAA"

    def test_filters_high_drawdown_for_low_risk(self, low_risk_profile):
        candidates = [
            {"ticker": "AAA", "health_score": 90, "annualized_volatility": 0.10, "max_drawdown": -0.05},
            {"ticker": "BBB", "health_score": 95, "annualized_volatility": 0.10, "max_drawdown": -0.25},
        ]
        result = filter_and_rank_candidates(candidates, low_risk_profile)
        assert len(result) == 1
        assert result[0]["ticker"] == "AAA"

    def test_high_risk_profile_tolerates_more(self, high_risk_profile):
        candidates = [
            {"ticker": "AAA", "health_score": 90, "annualized_volatility": 0.30, "max_drawdown": -0.25},
            {"ticker": "BBB", "health_score": 85, "annualized_volatility": 0.35, "max_drawdown": -0.30},
        ]
        result = filter_and_rank_candidates(candidates, high_risk_profile)
        assert len(result) == 2

    def test_ranks_by_health_score_descending(self, high_risk_profile):
        candidates = [
            {"ticker": "AAA", "health_score": 70, "annualized_volatility": 0.20, "max_drawdown": -0.15},
            {"ticker": "BBB", "health_score": 90, "annualized_volatility": 0.20, "max_drawdown": -0.15},
            {"ticker": "CCC", "health_score": 80, "annualized_volatility": 0.20, "max_drawdown": -0.15},
        ]
        result = filter_and_rank_candidates(candidates, high_risk_profile)
        assert result[0]["ticker"] == "BBB"
        assert result[1]["ticker"] == "CCC"
        assert result[2]["ticker"] == "AAA"

    def test_max_3_results(self, high_risk_profile):
        candidates = [
            {"ticker": f"T{i}", "health_score": 80 - i, "annualized_volatility": 0.15, "max_drawdown": -0.10}
            for i in range(5)
        ]
        result = filter_and_rank_candidates(candidates, high_risk_profile)
        assert len(result) == 3

    def test_none_values_not_filtered(self, low_risk_profile):
        candidates = [
            {"ticker": "AAA", "health_score": 90, "annualized_volatility": None, "max_drawdown": None},
        ]
        result = filter_and_rank_candidates(candidates, low_risk_profile)
        assert len(result) == 1

    def test_empty_candidates(self, low_risk_profile):
        result = filter_and_rank_candidates([], low_risk_profile)
        assert result == []


def test_low_profile_fit_candidates_filtered():
    from insight_engine.domain.entities import UserProfile
    from insight_engine.domain.enums import InvestmentObjective, RiskProfile
    from insight_engine.rules.alternative_rules import filter_and_rank_candidates

    profile = UserProfile(
        risk=RiskProfile.moderate, horizon="long", objective=InvestmentObjective.growth
    )
    candidates = [
        {"ticker": "FITS", "health_score": 60, "profile_fit_score": 70,
         "annualized_volatility": 0.15, "max_drawdown": -0.10},
        {"ticker": "NOFIT", "health_score": 90, "profile_fit_score": 35,
         "annualized_volatility": 0.15, "max_drawdown": -0.10},
        {"ticker": "UNKNOWN_FIT", "health_score": 50,
         "annualized_volatility": 0.15, "max_drawdown": -0.10},
    ]

    result = filter_and_rank_candidates(candidates, profile)
    tickers = [c["ticker"] for c in result]

    assert "NOFIT" not in tickers  # high health but poor fit is still excluded
    assert "FITS" in tickers
    assert "UNKNOWN_FIT" in tickers  # missing fit is not penalized


def test_goal_role_match_ranks_first():
    from insight_engine.domain.entities import UserProfile
    from insight_engine.domain.enums import InvestmentObjective, PortfolioRole, RiskProfile
    from insight_engine.rules.alternative_rules import filter_and_rank_candidates

    income = UserProfile(
        risk=RiskProfile.moderate, horizon="long", objective=InvestmentObjective.income
    )
    candidates = [
        {"ticker": "TECH", "health_score": 90, "profile_fit_score": 60,
         "role": PortfolioRole.GROWTH_TECH.value,
         "annualized_volatility": 0.15, "max_drawdown": -0.10},
        {"ticker": "DIVY", "health_score": 70, "profile_fit_score": 60,
         "role": PortfolioRole.DIVIDEND_INCOME.value,
         "annualized_volatility": 0.15, "max_drawdown": -0.10},
    ]
    result = filter_and_rank_candidates(candidates, income)
    # Income goal prefers the dividend role even though tech has higher health
    assert result[0]["ticker"] == "DIVY"
