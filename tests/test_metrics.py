import numpy as np
import pandas as pd

from insight_engine.services.metrics import (
    calculate_annualized_volatility,
    calculate_max_drawdown,
    calculate_metrics,
    calculate_parabolic_sar,
    calculate_sma,
)


def test_sma_basic():
    prices = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
    result = calculate_sma(prices, 3)
    assert result is not None
    assert abs(result - 13.0) < 0.01  # avg of last 3: (12+13+14)/3


def test_sma_insufficient_data():
    prices = pd.Series([10.0, 11.0])
    result = calculate_sma(prices, 5)
    assert result is None


def test_annualized_volatility():
    np.random.seed(42)
    prices = pd.Series(100 + np.cumsum(np.random.randn(252) * 1.0))
    vol = calculate_annualized_volatility(prices)
    assert vol is not None
    assert 0.0 < vol < 1.0  # reasonable annual vol range


def test_annualized_volatility_insufficient_data():
    prices = pd.Series([100.0, 101.0, 102.0])
    vol = calculate_annualized_volatility(prices)
    assert vol is None


def test_max_drawdown():
    prices = pd.Series([100.0, 110.0, 90.0, 95.0, 80.0, 100.0])
    dd = calculate_max_drawdown(prices)
    assert dd is not None
    # Max drawdown: from 110 to 80 = -27.27%
    assert abs(dd - (-30.0 / 110.0)) < 0.01


def test_max_drawdown_no_drawdown():
    prices = pd.Series([100.0, 101.0, 102.0, 103.0])
    dd = calculate_max_drawdown(prices)
    assert dd is not None
    assert dd == 0.0


def test_calculate_metrics_with_empty_info():
    hist = pd.DataFrame({"Close": [100.0] * 250})
    info = {}
    metrics = calculate_metrics(hist, info)
    assert metrics.current_price == 100.0
    assert metrics.pe_ratio is None
    assert metrics.revenue_growth is None


def test_calculate_metrics_with_full_info():
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(300) * 0.5)
    hist = pd.DataFrame({"Close": prices})
    info = {
        "trailingPE": 20.0,
        "forwardPE": 18.0,
        "revenueGrowth": 0.12,
        "profitMargins": 0.18,
        "debtToEquity": 80.0,  # yfinance reports as percentage
    }
    metrics = calculate_metrics(hist, info)
    assert metrics.sma_50 is not None
    assert metrics.sma_200 is not None
    assert metrics.pe_ratio == 20.0
    assert metrics.revenue_growth == 0.12
    assert metrics.profit_margin == 0.18
    assert abs(metrics.debt_to_equity - 0.80) < 0.01


def test_parabolic_sar_uptrend():
    """SAR should be below price in an uptrend."""
    n = 50
    high = pd.Series([100.0 + i * 1.5 for i in range(n)])
    low = pd.Series([98.0 + i * 1.5 for i in range(n)])
    close = pd.Series([99.0 + i * 1.5 for i in range(n)])
    sar = calculate_parabolic_sar(high, low, close)
    assert sar is not None
    assert sar < close.iloc[-1]


def test_parabolic_sar_downtrend():
    """SAR should be above price in a downtrend."""
    n = 50
    high = pd.Series([200.0 - i * 1.5 for i in range(n)])
    low = pd.Series([198.0 - i * 1.5 for i in range(n)])
    close = pd.Series([199.0 - i * 1.5 for i in range(n)])
    sar = calculate_parabolic_sar(high, low, close)
    assert sar is not None
    assert sar > close.iloc[-1]


def test_parabolic_sar_insufficient_data():
    """SAR returns None when fewer than 2 data points."""
    high = pd.Series([100.0])
    low = pd.Series([98.0])
    close = pd.Series([99.0])
    sar = calculate_parabolic_sar(high, low, close)
    assert sar is None


def test_parabolic_sar_in_calculate_metrics():
    """SAR is included in calculate_metrics when High/Low are available."""
    np.random.seed(42)
    n = 100
    base = 100 + np.cumsum(np.random.randn(n) * 0.5)
    hist = pd.DataFrame({
        "Close": base,
        "High": base + 1.0,
        "Low": base - 1.0,
    })
    metrics = calculate_metrics(hist, {})
    assert metrics.parabolic_sar is not None


def test_parabolic_sar_none_without_high_low():
    """SAR is None when High/Low columns are missing."""
    hist = pd.DataFrame({"Close": [100.0] * 50})
    metrics = calculate_metrics(hist, {})
    assert metrics.parabolic_sar is None


def test_calculate_metrics_sanitizes_nan():
    """yfinance reports missing values as NaN; they must become None, not NaN."""
    n = 250
    close = pd.Series(np.linspace(100, 120, n))
    hist = pd.DataFrame({"Close": close, "High": close + 1, "Low": close - 1})
    info = {
        "trailingPE": float("nan"),
        "forwardPE": float("nan"),
        "revenueGrowth": float("nan"),
        "profitMargins": 0.2,
        "debtToEquity": float("nan"),
    }

    metrics = calculate_metrics(hist, info)

    assert metrics.pe_ratio is None
    assert metrics.pe_historical_avg is None
    assert metrics.revenue_growth is None
    assert metrics.debt_to_equity is None
    assert metrics.profit_margin == 0.2
    assert metrics.current_price is not None


def test_normalize_dividend_yield():
    from insight_engine.services.metrics import normalize_dividend_yield

    # trailingAnnualDividendYield is a fraction and preferred
    assert normalize_dividend_yield({"trailingAnnualDividendYield": 0.025}) == 0.025
    # dividendYield is a percent in newer yfinance -> divided by 100
    assert normalize_dividend_yield({"dividendYield": 2.5}) == 0.025
    # trailing preferred over raw when both present
    assert normalize_dividend_yield(
        {"trailingAnnualDividendYield": 0.02, "dividendYield": 9.9}
    ) == 0.02
    # neither -> None
    assert normalize_dividend_yield({}) is None


def test_calculate_metrics_populates_dividend_yield():
    n = 250
    close = pd.Series(np.linspace(100, 120, n))
    hist = pd.DataFrame({"Close": close, "High": close + 1, "Low": close - 1})
    metrics = calculate_metrics(hist, {"dividendYield": 3.0})
    assert abs(metrics.dividend_yield - 0.03) < 1e-9
