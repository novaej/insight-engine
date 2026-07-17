from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from insight_engine.api.deps import get_current_user
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
from insight_engine.domain.models import User
from insight_engine.main import app


def _assign_id(obj):
    if getattr(obj, "id", None) is None:
        obj.id = 1


async def _mock_session():
    session = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock(side_effect=_assign_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)
    yield session


def _fake_user() -> User:
    user = User(email="tester@example.com", name="Tester")
    user.id = 1
    return user


async def _mock_current_user():
    return _fake_user()


app.dependency_overrides[get_session] = _mock_session
app.dependency_overrides[get_current_user] = _mock_current_user
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
@patch("insight_engine.api.portfolio_routes.generate_batch_explanations")
@patch("insight_engine.api.portfolio_routes.analyze_asset")
def test_analyze_portfolio_endpoint(mock_analyze, mock_explain, mock_provider, mock_prepare, mock_resolve):
    mock_analyze.side_effect = lambda ticker, *a, **kw: (_mock_insight(ticker.upper()), {"quoteType": "EQUITY"})
    mock_explain.return_value = None

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


def test_analyze_portfolio_without_assets_and_no_positions():
    response = client.post(
        "/portfolio/analyze",
        json={"user_profile": {"risk": "moderate", "horizon": "long", "goal": "growth"}},
    )
    assert response.status_code == 400


def test_register_user():
    response = client.post(
        "/users",
        json={"email": "jon@example.com", "password": "supersecret", "name": "Jon"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "jon@example.com"
    assert "token" not in data
    assert "password" not in data


def test_register_user_invalid_email():
    response = client.post(
        "/users", json={"email": "not-an-email", "password": "supersecret"}
    )
    assert response.status_code == 422


def test_login_success():
    from insight_engine.api.deps import hash_password

    user = MagicMock()
    user.password_hash = hash_password("supersecret")

    async def _session_with_user():
        session = MagicMock()
        session.commit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        session.execute = AsyncMock(return_value=mock_result)
        yield session

    from insight_engine.main import app as _app

    _app.dependency_overrides[get_session] = _session_with_user
    try:
        response = client.post(
            "/login", json={"email": "jon@example.com", "password": "supersecret"}
        )
        assert response.status_code == 200
        assert response.json()["token"]
        assert user.api_token_hash  # rotated on login

        bad = client.post(
            "/login", json={"email": "jon@example.com", "password": "wrongpass"}
        )
        assert bad.status_code == 401
    finally:
        _app.dependency_overrides[get_session] = _mock_session


def test_auth_required_without_token():
    del app.dependency_overrides[get_current_user]
    try:
        no_header = client.get("/users/me")
        assert no_header.status_code == 401

        bad_token = client.get(
            "/users/me", headers={"Authorization": "Bearer bogus-token"}
        )
        assert bad_token.status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = _mock_current_user


def test_me_returns_authenticated_user():
    response = client.get("/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == "tester@example.com"


def test_update_me_password_requires_current_password():
    response = client.patch(
        "/users/me", json={"password": "newpassword123"}
    )
    assert response.status_code == 401

    rename = client.patch("/users/me", json={"name": "New Name"})
    assert rename.status_code == 200
    assert rename.json()["name"] == "New Name"


def test_delete_me():
    response = client.delete("/users/me")
    assert response.status_code == 204


def test_add_lot_and_missing_position():
    response = client.post(
        "/portfolio/positions",
        json={"ticker": "aapl", "quantity": 2.5, "purchase_price": 180.0},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["purchase_price"] == 180.0

    missing = client.delete("/portfolio/positions/999")
    assert missing.status_code == 404


def test_aggregate_lots():
    from insight_engine.api.portfolio_routes import _aggregate_lots
    from insight_engine.api.schemas import PortfolioAsset

    lots = [
        PortfolioAsset(ticker="AAPL", quantity=2.0, purchase_price=180.0),
        PortfolioAsset(ticker="aapl", quantity=1.0, purchase_price=210.0),
        PortfolioAsset(ticker="MSFT", quantity=5.0),
    ]
    aggregated = _aggregate_lots(lots)
    assert len(aggregated) == 2

    aapl = next(a for a in aggregated if a.ticker == "AAPL")
    assert aapl.quantity == 3.0
    assert aapl.purchase_price == 190.0  # (2*180 + 1*210) / 3

    msft = next(a for a in aggregated if a.ticker == "MSFT")
    assert msft.quantity == 5.0
    assert msft.purchase_price is None


def test_insight_history_empty():
    response = client.get("/insights?ticker=AAPL")
    assert response.status_code == 200
    assert response.json() == {"total": 0, "insights": []}
