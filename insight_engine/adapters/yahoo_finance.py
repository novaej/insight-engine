import pandas as pd
import yfinance as yf

from insight_engine.adapters.retry import with_retry


class YahooFinanceProvider:
    @with_retry()
    def fetch_history(self, ticker: str, period: str = "2y") -> pd.DataFrame:
        return yf.Ticker(ticker).history(period=period)

    @with_retry()
    def fetch_info(self, ticker: str) -> dict:
        return yf.Ticker(ticker).info

    def fetch_news(self, ticker: str) -> list[dict]:
        try:
            return self._fetch_news(ticker)
        except Exception:
            return []

    def fetch_holdings(self, etf_ticker: str) -> list[str]:
        """Top holding tickers of an ETF. Empty list if unavailable.

        Indices (e.g. ^GSPC) and bond/foreign funds have no usable equity
        holdings and return []."""
        try:
            return self._fetch_holdings(etf_ticker)
        except Exception:
            return []

    @with_retry()
    def _fetch_news(self, ticker: str) -> list[dict]:
        return yf.Ticker(ticker).news or []

    @with_retry()
    def _fetch_holdings(self, etf_ticker: str) -> list[str]:
        top = yf.Ticker(etf_ticker).funds_data.top_holdings
        return [str(t) for t in top.index]
