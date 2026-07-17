from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from insight_engine.domain.entities import (
    AlternativeSuggestion,
    DimensionResults,
    Insight,
    MetricsSummary,
    UserProfile,
)
from insight_engine.domain.enums import (
    AssetState,
    Fundamentals,
    Horizon,
    InvestmentObjective,
    MarketContext,
    PortfolioRole,
    RiskLevel,
    RiskProfile,
    Trend,
    Valuation,
)
from insight_engine.services.alternatives import (
    prepare_alternatives_context,
    resolve_alternatives,
)


@pytest.fixture
def mock_market_data_provider():
    provider = MagicMock()

    # Default: return empty news
    provider.fetch_news.return_value = []

    # Default: return minimal price history
    dates = pd.date_range(start="2024-01-01", periods=250, freq="B")
    prices = 100 + np.cumsum(np.random.randn(250) * 0.5)
    hist = pd.DataFrame(
        {"Close": prices, "High": prices + 1, "Low": prices - 1},
        index=dates,
    )
    provider.fetch_history.return_value = hist

    # Default: return basic info
    provider.fetch_info.return_value = {
        "quoteType": "EQUITY",
        "sector": "Technology",
        "marketCap": 100_000_000_000,
        "trailingPE": 20.0,
        "revenueGrowth": 0.15,
        "profitMargins": 0.20,
        "debtToEquity": 50.0,
    }

    return provider


@pytest.fixture
def risky_insight():
    """An insight with poor health (bearish, weak fundamentals, high risk)."""
    return Insight(
        ticker="BAD",
        asset_state=AssetState.risky,
        dimensions=DimensionResults(
            trend=Trend.bearish,
            valuation=Valuation.expensive,
            fundamentals=Fundamentals.weak,
            risk_level=RiskLevel.high,
            market_context=MarketContext.adverse,
        ),
        metrics=MetricsSummary(
            annualized_volatility=0.50,
            max_drawdown=-0.40,
            debt_to_equity=3.0,
        ),
        horizon=Horizon.not_recommended,
    )


@pytest.fixture
def healthy_insight():
    """An insight with good health."""
    return Insight(
        ticker="GOOD",
        asset_state=AssetState.healthy,
        dimensions=DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.reasonable,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        ),
        metrics=MetricsSummary(
            annualized_volatility=0.15,
            max_drawdown=-0.10,
            debt_to_equity=0.5,
        ),
        horizon=Horizon.long_term,
    )


@pytest.fixture
def moderate_profile():
    return UserProfile(
        risk=RiskProfile.moderate,
        horizon="long",
        objective=InvestmentObjective.growth,
    )


class TestPrepareAlternativesContext:
    def test_triggers_for_risky_asset(self, risky_insight, moderate_profile, mock_market_data_provider):
        info = {"quoteType": "EQUITY", "sector": "Technology", "marketCap": 100_000_000_000}
        ctx = prepare_alternatives_context(risky_insight, info, moderate_profile, mock_market_data_provider)

        assert ctx is not None
        assert ctx["health_score"] < 50
        assert "trigger_reasons" in ctx
        assert risky_insight.portfolio_role == PortfolioRole.GROWTH_TECH
        assert risky_insight.scores is not None
        assert risky_insight.news_flags is not None

    def test_no_trigger_for_healthy_asset(self, healthy_insight, moderate_profile, mock_market_data_provider):
        info = {"quoteType": "EQUITY", "sector": "Technology", "marketCap": 100_000_000_000}
        ctx = prepare_alternatives_context(healthy_insight, info, moderate_profile, mock_market_data_provider)

        assert ctx is None
        assert healthy_insight.alternatives is not None
        assert healthy_insight.alternatives.triggered is False

    def test_news_flags_can_trigger(self, healthy_insight, moderate_profile, mock_market_data_provider):
        mock_market_data_provider.fetch_news.return_value = [
            {"title": "SEC investigation into company practices"},
        ]
        info = {"quoteType": "EQUITY", "sector": "Technology", "marketCap": 100_000_000_000}
        ctx = prepare_alternatives_context(healthy_insight, info, moderate_profile, mock_market_data_provider)

        assert ctx is not None
        assert any("regulatory" in r.lower() for r in ctx["trigger_reasons"])

    def test_news_fetch_failure_graceful(self, risky_insight, moderate_profile, mock_market_data_provider):
        mock_market_data_provider.fetch_news.side_effect = Exception("Network error")
        info = {"quoteType": "EQUITY", "sector": "Technology", "marketCap": 100_000_000_000}
        ctx = prepare_alternatives_context(risky_insight, info, moderate_profile, mock_market_data_provider)

        # Should still work (news flags all False, but health score triggers)
        assert ctx is not None
        assert risky_insight.news_flags is not None


class TestResolveAlternatives:
    def test_fallback_candidates_used_when_no_ai(self, risky_insight, moderate_profile, mock_market_data_provider):
        risky_insight.portfolio_role = PortfolioRole.GROWTH_TECH
        alternatives_ctx = {
            "health_score": 20,
            "profile_fit_score": 30,
            "portfolio_role": "GROWTH_TECH",
            "trigger_reasons": ["Low health score (20/100)"],
            "news_flags": {"regulatory_risk": False, "earnings_negative": False,
                          "management_change": False, "litigation_risk": False},
        }

        with patch("insight_engine.services.alternatives.get_fallback_candidates") as mock_get:
            mock_get.return_value = ["QQQ", "VGT"]

            resolve_alternatives(
                risky_insight, moderate_profile, mock_market_data_provider,
                alternatives_ctx, use_ai=False,
            )

        assert risky_insight.alternatives is not None
        assert risky_insight.alternatives.triggered is True
        assert len(risky_insight.alternatives.trigger_reasons) > 0

    def test_ai_suggestions_used_when_available(self, risky_insight, moderate_profile, mock_market_data_provider):
        risky_insight.portfolio_role = PortfolioRole.GROWTH_TECH
        risky_insight._ai_suggestions = [
            AlternativeSuggestion(ticker="MSFT", reason="Strong fundamentals"),
            AlternativeSuggestion(ticker="AAPL", reason="Low volatility"),
        ]
        alternatives_ctx = {
            "health_score": 20,
            "profile_fit_score": 30,
            "portfolio_role": "GROWTH_TECH",
            "trigger_reasons": ["Low health score (20/100)"],
            "news_flags": {"regulatory_risk": False, "earnings_negative": False,
                          "management_change": False, "litigation_risk": False},
        }

        resolve_alternatives(
            risky_insight, moderate_profile, mock_market_data_provider,
            alternatives_ctx, use_ai=True,
        )

        assert risky_insight.alternatives is not None
        assert risky_insight.alternatives.triggered is True
        # ai_suggestions cleaned up
        assert not hasattr(risky_insight, "_ai_suggestions")

    def test_fallback_when_ai_suggestions_empty(self, risky_insight, moderate_profile, mock_market_data_provider):
        risky_insight.portfolio_role = PortfolioRole.GROWTH_TECH
        # No _ai_suggestions attribute set
        alternatives_ctx = {
            "health_score": 20,
            "profile_fit_score": 30,
            "portfolio_role": "GROWTH_TECH",
            "trigger_reasons": ["Low health score (20/100)"],
            "news_flags": {"regulatory_risk": False, "earnings_negative": False,
                          "management_change": False, "litigation_risk": False},
        }

        with patch("insight_engine.services.alternatives.get_fallback_candidates") as mock_get:
            mock_get.return_value = ["QQQ"]

            resolve_alternatives(
                risky_insight, moderate_profile, mock_market_data_provider,
                alternatives_ctx, use_ai=True,
            )

        assert risky_insight.alternatives is not None
        assert risky_insight.alternatives.triggered is True


class TestEndToEnd:
    def test_full_flow_trigger_and_resolve(self, risky_insight, moderate_profile, mock_market_data_provider):
        info = {"quoteType": "EQUITY", "sector": "Technology", "marketCap": 100_000_000_000}

        ctx = prepare_alternatives_context(risky_insight, info, moderate_profile, mock_market_data_provider)
        assert ctx is not None

        with patch("insight_engine.services.alternatives.get_fallback_candidates") as mock_get:
            mock_get.return_value = ["QQQ", "MSFT"]

            resolve_alternatives(
                risky_insight, moderate_profile, mock_market_data_provider,
                ctx, use_ai=False,
            )

        assert risky_insight.alternatives.triggered is True
        assert risky_insight.portfolio_role is not None
        assert risky_insight.scores is not None

    def test_full_flow_no_trigger(self, healthy_insight, moderate_profile, mock_market_data_provider):
        info = {"quoteType": "EQUITY", "sector": "Technology", "marketCap": 100_000_000_000}

        ctx = prepare_alternatives_context(healthy_insight, info, moderate_profile, mock_market_data_provider)
        assert ctx is None
        assert healthy_insight.alternatives.triggered is False
        # Scores and role still populated
        assert healthy_insight.scores is not None
        assert healthy_insight.portfolio_role is not None


class TestCandidateQuality:
    def test_held_tickers_never_suggested(
        self, risky_insight, moderate_profile, mock_market_data_provider
    ):
        risky_insight.portfolio_role = PortfolioRole.GROWTH_TECH
        risky_insight._ai_suggestions = [
            AlternativeSuggestion(ticker="AAPL", reason="held"),
            AlternativeSuggestion(ticker="MSFT", reason="not held"),
        ]

        with patch(
            "insight_engine.services.alternatives.get_fallback_candidates",
            return_value=[],
        ):
            resolve_alternatives(
                risky_insight,
                moderate_profile,
                mock_market_data_provider,
                {"trigger_reasons": ["Low health score"]},
                use_ai=True,
                held_tickers={"AAPL", "BAD"},
            )

        tickers = [s.ticker for s in risky_insight.alternatives.suggestions]
        assert "AAPL" not in tickers
        assert "BAD" not in tickers

    def test_falls_back_to_config_when_ai_candidates_filtered_out(
        self, risky_insight, moderate_profile, mock_market_data_provider
    ):
        risky_insight.portfolio_role = PortfolioRole.GROWTH_TECH
        # The only AI suggestion is the held ticker itself -> validated list empty
        risky_insight._ai_suggestions = [
            AlternativeSuggestion(ticker="BAD", reason="self")
        ]

        with patch(
            "insight_engine.services.alternatives.get_fallback_candidates",
            return_value=["VGT"],
        ) as mock_fallback:
            resolve_alternatives(
                risky_insight,
                moderate_profile,
                mock_market_data_provider,
                {"trigger_reasons": ["Low health score"]},
                use_ai=True,
            )

        mock_fallback.assert_called_once()
        assert risky_insight.alternatives.triggered

    def test_suggestions_carry_profile_fit(
        self, risky_insight, moderate_profile, mock_market_data_provider
    ):
        risky_insight.portfolio_role = PortfolioRole.GROWTH_TECH
        risky_insight._ai_suggestions = [
            AlternativeSuggestion(ticker="MSFT", reason="candidate")
        ]

        resolve_alternatives(
            risky_insight,
            moderate_profile,
            mock_market_data_provider,
            {"trigger_reasons": ["Low health score"]},
            use_ai=True,
        )

        for suggestion in risky_insight.alternatives.suggestions:
            assert suggestion.profile_fit_score is not None
            assert suggestion.profile_fit_score >= 50
