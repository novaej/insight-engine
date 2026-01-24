import pandas as pd
import yfinance as yf


def fetch_ticker_data(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Fetch historical price data for a ticker."""
    t = yf.Ticker(ticker)
    hist = t.history(period=period)
    return hist


def fetch_ticker_info(ticker: str) -> dict:
    """Fetch fundamental info for a ticker."""
    t = yf.Ticker(ticker)
    return t.info


def fetch_sp500_data(period: str = "1y") -> pd.DataFrame:
    """Fetch S&P 500 (^GSPC) historical data for market context."""
    return fetch_ticker_data("^GSPC", period=period)
