from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from insight_engine.database import get_session
from insight_engine.domain.entities import DimensionResults, Insight, MetricsSummary
from insight_engine.domain.enums import (
    AssetState,
    Fundamentals,
    Horizon,
    MarketContext,
    RiskLevel,
    Trend,
    Valuation,
)
from insight_engine.main import app


async def _mock_session():
    session = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)
    yield session


app.dependency_overrides[get_session] = _mock_session
client = TestClient(app)


def _mock_insight(ticker="AAPL"):
    return Insight(
        ticker=ticker,
        asset_state=AssetState.healthy,
        dimensions=DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.reasonable,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        ),
        metrics=MetricsSummary(
            current_price=150.0,
            sma_50=145.0,
            sma_200=135.0,
            pe_ratio=20.0,
            revenue_growth=0.12,
            profit_margin=0.20,
            debt_to_equity=0.5,
            annualized_volatility=0.18,
            max_drawdown=-0.12,
        ),
        horizon=Horizon.long_term,
        scenario="Stable growth expected with minor corrections",
        risks=["Market volatility", "Valuation compression"],
        explanation="The asset shows strong fundamentals with a bullish trend.",
    )


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("insight_engine.api.asset_routes.resolve_alternatives")
@patch("insight_engine.api.asset_routes.prepare_alternatives_context", return_value=None)
@patch("insight_engine.api.asset_routes.get_market_data_provider")
@patch("insight_engine.api.asset_routes.generate_explanation")
@patch("insight_engine.api.asset_routes.analyze_asset")
def test_analyze_asset_endpoint(mock_analyze, mock_explain, mock_provider, mock_prepare, mock_resolve):
    insight = _mock_insight()
    mock_analyze.return_value = (insight, {"quoteType": "EQUITY", "sector": "Technology"})
    mock_explain.return_value = insight

    response = client.post(
        "/assets/analyze",
        json={
            "ticker": "AAPL",
            "user_profile": {"risk": "moderate", "horizon": "long", "goal": "growth"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["asset_state"] == "healthy"
    assert data["dimensions"]["trend"] == "bullish"
    assert data["horizon"] == "long_term"
    assert len(data["risks"]) <= 3


@patch("insight_engine.api.asset_routes.resolve_alternatives")
@patch("insight_engine.api.asset_routes.prepare_alternatives_context", return_value=None)
@patch("insight_engine.api.asset_routes.get_market_data_provider")
@patch("insight_engine.api.asset_routes.generate_explanation")
@patch("insight_engine.api.asset_routes.analyze_asset")
def test_analyze_asset_without_profile(mock_analyze, mock_explain, mock_provider, mock_prepare, mock_resolve):
    insight = _mock_insight("MSFT")
    mock_analyze.return_value = (insight, {"quoteType": "EQUITY"})
    mock_explain.return_value = insight

    response = client.post("/assets/analyze", json={"ticker": "MSFT"})
    assert response.status_code == 200
    assert response.json()["ticker"] == "MSFT"


@patch("insight_engine.api.portfolio_routes.resolve_alternatives")
@patch("insight_engine.api.portfolio_routes.prepare_alternatives_context", return_value=None)
@patch("insight_engine.api.portfolio_routes.get_market_data_provider")
@patch("insight_engine.api.portfolio_routes.generate_explanation")
@patch("insight_engine.api.portfolio_routes.analyze_asset")
def test_analyze_portfolio_endpoint(mock_analyze, mock_explain, mock_provider, mock_prepare, mock_resolve):
    mock_analyze.side_effect = lambda ticker, *a, **kw: (_mock_insight(ticker.upper()), {"quoteType": "EQUITY"})
    mock_explain.side_effect = lambda insight, *a, **kw: insight

    response = client.post(
        "/portfolio/analyze",
        json={
            "user_profile": {"risk": "moderate", "horizon": "long", "goal": "growth"},
            "assets": [
                {"ticker": "AAPL", "quantity": 10},
                {"ticker": "MSFT", "quantity": 5},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_assets"] == 2
    assert len(data["insights"]) == 2
    assert data["overall_risk"] in ["low", "medium", "high"]


def test_analyze_asset_invalid_ticker():
    response = client.post("/assets/analyze", json={"ticker": ""})
    assert response.status_code == 422


def test_portfolio_too_many_assets():
    response = client.post(
        "/portfolio/analyze",
        json={
            "user_profile": {"risk": "moderate", "horizon": "long", "goal": "growth"},
            "assets": [{"ticker": f"T{i}", "quantity": 1} for i in range(21)],
        },
    )
    assert response.status_code == 422
