import threading

from insight_engine.ports import MarketDataProvider


class CachingMarketDataProvider:
    """Request-scoped, thread-safe cache around a MarketDataProvider.

    Analyzing a portfolio fetches the same benchmark histories (and candidate
    data) repeatedly across worker threads; wrapping the provider once per
    request dedupes those calls.
    """

    def __init__(self, inner: MarketDataProvider):
        self._inner = inner
        self._cache: dict[tuple, object] = {}
        self._lock = threading.Lock()

    def _cached(self, key: tuple, fetch):
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        value = fetch()
        with self._lock:
            self._cache[key] = value
        return value

    def fetch_history(self, ticker: str, period: str = "2y"):
        return self._cached(
            ("history", ticker.upper(), period),
            lambda: self._inner.fetch_history(ticker, period),
        )

    def fetch_info(self, ticker: str) -> dict:
        return self._cached(
            ("info", ticker.upper()), lambda: self._inner.fetch_info(ticker)
        )

    def fetch_news(self, ticker: str) -> list[dict]:
        return self._cached(
            ("news", ticker.upper()), lambda: self._inner.fetch_news(ticker)
        )

    def fetch_holdings(self, etf_ticker: str) -> list[str]:
        return self._cached(
            ("holdings", etf_ticker.upper()),
            lambda: self._inner.fetch_holdings(etf_ticker),
        )
