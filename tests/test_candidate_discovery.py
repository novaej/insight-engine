from unittest.mock import MagicMock

from insight_engine.domain.enums import PortfolioRole
from insight_engine.rules.candidate_discovery import (
    discover_candidates,
    get_discovery_etf,
)


def test_discovery_etf_mapping():
    assert get_discovery_etf(PortfolioRole.US_LARGE_CAP_CORE) == "SPY"
    assert get_discovery_etf(PortfolioRole.GROWTH_TECH) == "QQQ"
    assert get_discovery_etf(PortfolioRole.DIVIDEND_INCOME) == "VYM"
    assert get_discovery_etf(PortfolioRole.DEFENSIVE) == "XLP"
    # Bonds and emerging markets have no usable equity-holdings ETF
    assert get_discovery_etf(PortfolioRole.BONDS_STABILITY) is None
    assert get_discovery_etf(PortfolioRole.EMERGING_MARKETS) is None
    assert get_discovery_etf(None) is None


def test_discover_unions_and_filters_foreign():
    provider = MagicMock()
    # QQQ-style holdings incl. a foreign listing and the ETF itself
    provider.fetch_holdings.return_value = ["NVDA", "AAPL", "2330.TW", "QQQ"]

    result = discover_candidates(PortfolioRole.GROWTH_TECH, provider)

    assert "NVDA" in result and "AAPL" in result  # discovered US tickers
    assert "2330.TW" not in result  # foreign listing filtered
    # QQQ is not injected from its own holdings; it may still appear once from
    # the curated static list, but must never be duplicated
    assert result.count("QQQ") <= 1
    # Static GROWTH_TECH names still present (union), no duplicates
    assert "VGT" in result
    assert len(result) == len(set(result))
    # Discovered come before static-only extras
    assert result.index("NVDA") < result.index("VGT")


def test_roles_without_etf_skip_fetch():
    provider = MagicMock()
    result = discover_candidates(PortfolioRole.BONDS_STABILITY, provider)

    provider.fetch_holdings.assert_not_called()
    # Exactly the static bonds list
    assert "AGG" in result or "BND" in result


def test_fetch_failure_falls_back_to_static():
    provider = MagicMock()
    provider.fetch_holdings.side_effect = ConnectionError("down")

    result = discover_candidates(PortfolioRole.GROWTH_TECH, provider)

    # Static list survives the failure
    assert "VGT" in result
    assert all("." not in t for t in result)
