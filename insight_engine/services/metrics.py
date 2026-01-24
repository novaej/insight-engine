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


def calculate_parabolic_sar(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    initial_af: float = 0.02,
    step: float = 0.02,
    max_af: float = 0.20,
) -> float | None:
    """Calculate the Parabolic SAR and return the latest value.

    Uses the standard Wilder algorithm with configurable acceleration factor.
    """
    if len(close) < 2:
        return None

    n = len(close)
    sar = [0.0] * n
    af = initial_af
    is_long = bool(close.iloc[1] >= close.iloc[0])

    if is_long:
        sar[0] = float(low.iloc[0])
        ep = float(high.iloc[0])
    else:
        sar[0] = float(high.iloc[0])
        ep = float(low.iloc[0])

    for i in range(1, n):
        prev_sar = sar[i - 1]
        sar[i] = prev_sar + af * (ep - prev_sar)

        if is_long:
            # Clamp SAR to not exceed prior two lows
            sar[i] = min(sar[i], float(low.iloc[i - 1]))
            if i >= 2:
                sar[i] = min(sar[i], float(low.iloc[i - 2]))

            if float(low.iloc[i]) < sar[i]:
                # Reverse to short
                is_long = False
                sar[i] = ep
                ep = float(low.iloc[i])
                af = initial_af
            else:
                if float(high.iloc[i]) > ep:
                    ep = float(high.iloc[i])
                    af = min(af + step, max_af)
        else:
            # Clamp SAR to not be below prior two highs
            sar[i] = max(sar[i], float(high.iloc[i - 1]))
            if i >= 2:
                sar[i] = max(sar[i], float(high.iloc[i - 2]))

            if float(high.iloc[i]) > sar[i]:
                # Reverse to long
                is_long = True
                sar[i] = ep
                ep = float(high.iloc[i])
                af = initial_af
            else:
                if float(low.iloc[i]) < ep:
                    ep = float(low.iloc[i])
                    af = min(af + step, max_af)

    return sar[-1]


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
    high = hist["High"] if "High" in hist.columns else pd.Series(dtype=float)
    low = hist["Low"] if "Low" in hist.columns else pd.Series(dtype=float)

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

    parabolic_sar = None
    if len(high) >= 2 and len(low) >= 2:
        parabolic_sar = calculate_parabolic_sar(high, low, close)

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
        parabolic_sar=parabolic_sar,
    )
