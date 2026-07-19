"""End-to-end analyze flow with only the market-data provider mocked.

Unlike test_api.py (which mocks analyze_asset wholesale), this exercises the real
pipeline — metrics, the five rule dimensions, synthesis, scoring, concentration,
and persistence — so the wiring between them is actually covered. No AI or network.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from insight_engine.api.deps import get_current_user
from insight_engine.database import get_session
from insight_engine.domain.models import User
from insight_engine.main import app


def _uptrend_history(n=260, start=100.0, slope=0.3):
    prices = pd.Series(start + slope * np.arange(n))
    return pd.DataFrame({"Close": prices, "High": prices + 1, "Low": prices - 1})


def _fake_provider():
    p = MagicMock()
    p.fetch_history.return_value = _uptrend_history()
    p.fetch_info.return_value = {
        "quoteType": "EQUITY",
        "sector": "Technology",
        "marketCap": 2_000_000_000_000,
        "trailingPE": 22.0,
        "forwardPE": 20.0,
        "revenueGrowth": 0.15,
        "profitMargins": 0.25,
        "debtToEquity": 40.0,
        "trailingAnnualDividendYield": 0.005,
    }
    p.fetch_news.return_value = []
    p.fetch_holdings.return_value = []
    return p


async def _session():
    s = MagicMock()
    s.commit = AsyncMock()
    s.flush = AsyncMock()
    s.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    s.execute = AsyncMock(return_value=result)
    yield s


async def _user():
    u = User(email="int@example.com", name="Int")
    u.id = 1
    return u


@pytest.fixture
def client():
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_current_user] = _user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides = saved


def test_full_portfolio_analyze_pipeline(client):
    with patch(
        "insight_engine.api.portfolio_routes.get_market_data_provider",
        return_value=_fake_provider(),
    ):
        response = client.post(
            "/portfolio/analyze",
            json={
                "user_profile": {"risk": "moderate", "horizon": "long", "goal": "growth"},
                "assets": [
                    {"ticker": "AAA", "quantity": 3, "purchase_price": 90.0},
                    {"ticker": "BBB", "quantity": 1, "purchase_price": 100.0},
                ],
                "use_ai": False,
                "include_alternatives": False,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_assets"] == 2
    assert data["overall_risk"] in ("low", "medium", "high")
    assert data["total_value"] is not None

    for insight in data["insights"]:
        # Real rules ran: every dimension and score is populated with valid values
        assert insight["asset_state"] in (
            "healthy", "healthy_but_expensive", "neutral", "risky", "unattractive"
        )
        assert insight["dimensions"]["trend"] in ("bullish", "sideways", "bearish")
        assert 0 <= insight["health_score"] <= 100
        assert 0 <= insight["profile_fit_score"] <= 100
        # Uptrending series with a role benchmark → market context evaluated
        assert insight["metrics"]["benchmark_ticker"] is not None
        # Position context computed from the provided lots
        assert insight["position"]["weight"] is not None
        # use_ai=false → no AI text
        assert insight["scenario"] == ""
