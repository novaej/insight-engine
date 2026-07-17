import pandas as pd
import yfinance as yf


class YahooFinanceProvider:
    def fetch_history(self, ticker: str, period: str = "2y") -> pd.DataFrame:
        t = yf.Ticker(ticker)
        return t.history(period=period)

    def fetch_info(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        return t.info

    def fetch_news(self, ticker: str) -> list[dict]:
        t = yf.Ticker(ticker)
        return t.news or []

    def fetch_holdings(self, etf_ticker: str) -> list[str]:
        """Top holding tickers of an ETF. Empty list if unavailable.

        Indices (e.g. ^GSPC) and bond/foreign funds have no usable equity
        holdings and return []."""
        try:
            top = yf.Ticker(etf_ticker).funds_data.top_holdings
            return [str(t) for t in top.index]
        except Exception:
            return []
