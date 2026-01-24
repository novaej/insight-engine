import pandas as pd
import yfinance as yf


class YahooFinanceProvider:
    def fetch_history(self, ticker: str, period: str = "2y") -> pd.DataFrame:
        t = yf.Ticker(ticker)
        return t.history(period=period)

    def fetch_info(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        return t.info
