import threading
from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from insight_engine.adapters.caching import CachingMarketDataProvider
from insight_engine.domain.enums import PortfolioRole
from insight_engine.rules.benchmark_rules import get_benchmark_ticker
from insight_engine.services.analysis import analyze_asset


def test_role_benchmark_mapping():
    assert get_benchmark_ticker(PortfolioRole.GROWTH_TECH) == "QQQ"
    assert get_benchmark_ticker(PortfolioRole.US_LARGE_CAP_CORE) == "^GSPC"
    assert get_benchmark_ticker(PortfolioRole.DIVIDEND_INCOME) == "VYM"
    assert get_benchmark_ticker(PortfolioRole.DEFENSIVE) == "XLP"
    assert get_benchmark_ticker(PortfolioRole.EMERGING_MARKETS) == "EEM"
    assert get_benchmark_ticker(PortfolioRole.BONDS_STABILITY) == "AGG"
    assert get_benchmark_ticker(None) == "^GSPC"


def _price_hist(n=250):
    prices = pd.Series(100 + np.cumsum(np.random.default_rng(1).normal(0, 0.5, n)))
    return pd.DataFrame({"Close": prices, "High": prices + 1, "Low": prices - 1})


def test_analyze_asset_uses_role_benchmark():
    provider = MagicMock()
    provider.fetch_history.return_value = _price_hist()
    provider.fetch_info.return_value = {"quoteType": "EQUITY", "sector": "Technology"}

    insight, _ = analyze_asset("NVDA", market_data_provider=provider)

    fetched = [call.args[0] for call in provider.fetch_history.call_args_list]
    assert "QQQ" in fetched  # GROWTH_TECH role → QQQ, not ^GSPC
    assert "^GSPC" not in fetched
    assert insight.metrics.benchmark_ticker == "QQQ"
    assert insight.metrics.benchmark_above_sma200 in (True, False)
    assert insight.portfolio_role == PortfolioRole.GROWTH_TECH


def test_analyze_asset_survives_benchmark_fetch_failure():
    provider = MagicMock()
    hist = _price_hist()

    def fetch_history(ticker, period="2y"):
        if ticker == "QQQ":
            raise ConnectionError("benchmark down")
        return hist

    provider.fetch_history.side_effect = fetch_history
    provider.fetch_info.return_value = {"quoteType": "EQUITY", "sector": "Technology"}

    insight, _ = analyze_asset("NVDA", market_data_provider=provider)

    # Transparency: ticker recorded, signal explicitly missing
    assert insight.metrics.benchmark_ticker == "QQQ"
    assert insight.metrics.benchmark_above_sma200 is None


def test_caching_provider_dedupes_fetches():
    inner = MagicMock()
    inner.fetch_history.return_value = _price_hist()
    cached = CachingMarketDataProvider(inner)

    def worker():
        cached.fetch_history("QQQ", "1y")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    cached.fetch_history("qqq", "1y")  # case-insensitive hit

    assert inner.fetch_history.call_count == 1

    cached.fetch_history("QQQ", "2y")  # different period is a different key
    assert inner.fetch_history.call_count == 2


def test_caching_provider_caches_holdings():
    inner = MagicMock()
    inner.fetch_holdings.return_value = ["NVDA", "AAPL"]
    cached = CachingMarketDataProvider(inner)

    cached.fetch_holdings("QQQ")
    cached.fetch_holdings("qqq")  # case-insensitive hit
    assert inner.fetch_holdings.call_count == 1
