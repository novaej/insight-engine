import numpy as np
import pandas as pd

from insight_engine.services.metrics import (
    calculate_annualized_volatility,
    calculate_max_drawdown,
    calculate_metrics,
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
