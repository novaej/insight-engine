import os

# Provide dummy values for required settings so the suite runs without a .env
# (e.g. in CI). External providers are mocked, so these are never used for real.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
os.environ.setdefault("AZURE_TRANSLATOR_KEY", "")
os.environ.setdefault("AZURE_TRANSLATOR_ENDPOINT", "")
os.environ.setdefault("AZURE_TRANSLATOR_REGION", "")

import numpy as np
import pandas as pd
import pytest

from insight_engine.domain.entities import DimensionResults, MetricsSummary, UserProfile
from insight_engine.domain.enums import (
    Fundamentals,
    InvestmentObjective,
    MarketContext,
    RiskLevel,
    RiskProfile,
    Trend,
    Valuation,
)


@pytest.fixture
def sample_price_series():
    """Generate a sample price series for testing."""
    np.random.seed(42)
    dates = pd.date_range(start="2022-01-01", periods=500, freq="B")
    prices = 100 + np.cumsum(np.random.randn(500) * 0.5)
    return pd.Series(prices, index=dates, name="Close")


@pytest.fixture
def bullish_metrics():
    """Metrics representing a bullish, healthy asset."""
    return MetricsSummary(
        sma_50=155.0,
        sma_200=140.0,
        current_price=160.0,
        pe_ratio=18.0,
        pe_historical_avg=20.0,
        revenue_growth=0.15,
        profit_margin=0.20,
        debt_to_equity=0.5,
        max_drawdown=-0.10,
        annualized_volatility=0.18,
        benchmark_above_sma200=True,
    )


@pytest.fixture
def bearish_metrics():
    """Metrics representing a bearish, risky asset."""
    return MetricsSummary(
        sma_50=130.0,
        sma_200=145.0,
        current_price=120.0,
        pe_ratio=30.0,
        pe_historical_avg=20.0,
        revenue_growth=-0.05,
        profit_margin=0.05,
        debt_to_equity=2.5,
        max_drawdown=-0.40,
        annualized_volatility=0.50,
        benchmark_above_sma200=False,
    )


@pytest.fixture
def healthy_dimensions():
    return DimensionResults(
        trend=Trend.bullish,
        valuation=Valuation.reasonable,
        fundamentals=Fundamentals.strong,
        risk_level=RiskLevel.low,
        market_context=MarketContext.favorable,
    )


@pytest.fixture
def risky_dimensions():
    return DimensionResults(
        trend=Trend.bearish,
        valuation=Valuation.expensive,
        fundamentals=Fundamentals.weak,
        risk_level=RiskLevel.high,
        market_context=MarketContext.adverse,
    )


@pytest.fixture
def sample_user_profile():
    return UserProfile(
        risk=RiskProfile.moderate,
        horizon="long",
        objective=InvestmentObjective.growth,
    )
