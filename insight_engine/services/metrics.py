import numpy as np
import pandas as pd

from insight_engine.domain.entities import MetricsSummary


def calculate_sma(prices: pd.Series, window: int) -> float | None:
    """Calculate Simple Moving Average for the given window."""
    if len(prices) < window:
        return None
    return float(prices.rolling(window=window).mean().iloc[-1])


def calculate_annualized_volatility(prices: pd.Series) -> float | None:
    """Calculate annualized volatility from daily returns."""
    if len(prices) < 20:
        return None
    returns = prices.pct_change().dropna()
    if len(returns) == 0:
        return None
    return float(returns.std() * np.sqrt(252))


def calculate_max_drawdown(prices: pd.Series) -> float | None:
    """Calculate maximum drawdown over the price series."""
    if len(prices) < 2:
        return None
    cummax = prices.cummax()
    drawdown = (prices - cummax) / cummax
    return float(drawdown.min())


def calculate_metrics(
    hist: pd.DataFrame, info: dict, sp500_hist: pd.DataFrame | None = None
) -> MetricsSummary:
    """Calculate all metrics from historical data and ticker info."""
    close = hist["Close"] if "Close" in hist.columns else pd.Series(dtype=float)

    sma_50 = calculate_sma(close, 50)
    sma_200 = calculate_sma(close, 200)
    current_price = float(close.iloc[-1]) if len(close) > 0 else None

    pe_ratio = info.get("trailingPE") or info.get("forwardPE")
    pe_historical_avg = info.get("fiveYearAvgDividendYield")  # proxy; see note below

    # For valuation, we compare current P/E against a reasonable benchmark.
    # yfinance doesn't provide historical P/E averages directly,
    # so we use sector average or a fixed multiplier approach.
    # For MVP, we'll use forwardPE vs trailingPE as a simple heuristic,
    # or fall back to a sector-average if available.
    trailing_pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    if trailing_pe and forward_pe and forward_pe > 0:
        pe_historical_avg = (trailing_pe + forward_pe) / 2
    else:
        pe_historical_avg = None

    revenue_growth = info.get("revenueGrowth")
    profit_margin = info.get("profitMargins")
    debt_to_equity = info.get("debtToEquity")
    if debt_to_equity is not None:
        debt_to_equity = debt_to_equity / 100.0  # yfinance reports as percentage

    max_drawdown = calculate_max_drawdown(close)
    annualized_volatility = calculate_annualized_volatility(close)

    sp500_above_sma200 = None
    if sp500_hist is not None and len(sp500_hist) > 0:
        sp500_close = sp500_hist["Close"]
        sp500_sma200 = calculate_sma(sp500_close, 200)
        if sp500_sma200 is not None and len(sp500_close) > 0:
            sp500_above_sma200 = float(sp500_close.iloc[-1]) > sp500_sma200

    return MetricsSummary(
        sma_50=sma_50,
        sma_200=sma_200,
        current_price=current_price,
        pe_ratio=pe_ratio,
        pe_historical_avg=pe_historical_avg,
        revenue_growth=revenue_growth,
        profit_margin=profit_margin,
        debt_to_equity=debt_to_equity,
        max_drawdown=max_drawdown,
        annualized_volatility=annualized_volatility,
        sp500_above_sma200=sp500_above_sma200,
    )
