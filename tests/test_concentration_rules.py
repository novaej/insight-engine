from insight_engine.api.schemas import PortfolioAsset
from insight_engine.domain.entities import (
    DimensionResults,
    Insight,
    MetricsSummary,
    PositionContext,
)
from insight_engine.domain.enums import (
    AssetState,
    ConcentrationState,
    Fundamentals,
    Horizon,
    MarketContext,
    PortfolioRole,
    RiskLevel,
    Trend,
    Valuation,
)
from insight_engine.rules.concentration_rules import (
    compute_position_contexts,
    determine_weighted_risk,
    evaluate_concentration,
)


def _insight(ticker, price=None, state=AssetState.healthy, role=None):
    return Insight(
        ticker=ticker,
        asset_state=state,
        dimensions=DimensionResults(
            trend=Trend.bullish,
            valuation=Valuation.reasonable,
            fundamentals=Fundamentals.strong,
            risk_level=RiskLevel.low,
            market_context=MarketContext.favorable,
        ),
        metrics=MetricsSummary(current_price=price),
        horizon=Horizon.long_term,
        portfolio_role=role,
    )


class TestComputePositionContexts:
    def test_weights_sum_to_one(self):
        assets = [
            PortfolioAsset(ticker="AAPL", quantity=2.0),
            PortfolioAsset(ticker="MSFT", quantity=1.0),
        ]
        insights = [_insight("AAPL", price=100.0), _insight("MSFT", price=200.0)]

        total = compute_position_contexts(assets, insights)

        assert total == 400.0
        weights = [i.position.weight for i in insights]
        assert abs(sum(weights) - 1.0) < 1e-9
        assert insights[0].position.weight == 0.5  # 200 / 400
        assert insights[0].position.market_value == 200.0

    def test_missing_price_excluded_from_total(self):
        assets = [
            PortfolioAsset(ticker="AAPL", quantity=1.0),
            PortfolioAsset(ticker="MYST", quantity=5.0),
        ]
        insights = [_insight("AAPL", price=100.0), _insight("MYST", price=None)]

        total = compute_position_contexts(assets, insights)

        assert total == 100.0
        assert insights[0].position.weight == 1.0
        assert insights[1].position.market_value is None
        assert insights[1].position.weight is None

    def test_unrealized_gain(self):
        assets = [
            PortfolioAsset(ticker="AAPL", quantity=1.0, purchase_price=80.0),
            PortfolioAsset(ticker="MSFT", quantity=1.0, purchase_price=250.0),
        ]
        insights = [_insight("AAPL", price=100.0), _insight("MSFT", price=200.0)]

        compute_position_contexts(assets, insights)

        assert abs(insights[0].position.unrealized_gain_pct - 0.25) < 1e-9
        assert abs(insights[1].position.unrealized_gain_pct - (-0.2)) < 1e-9

    def test_no_prices_returns_none(self):
        assets = [PortfolioAsset(ticker="AAPL", quantity=1.0)]
        insights = [_insight("AAPL", price=None)]
        assert compute_position_contexts(assets, insights) is None


class TestEvaluateConcentration:
    def test_diversified(self):
        insights = [_insight(f"T{i}", price=100.0) for i in range(5)]
        for i in insights:
            i.position = PositionContext(quantity=1.0, weight=0.2)
        result = evaluate_concentration(insights)
        assert result.state == ConcentrationState.diversified
        assert result.flagged_tickers == []

    def test_position_over_25_percent_flagged(self):
        insights = [_insight("BIG"), _insight("SMALL")]
        insights[0].position = PositionContext(quantity=1.0, weight=0.7)
        insights[1].position = PositionContext(quantity=1.0, weight=0.3)
        result = evaluate_concentration(insights)
        assert result.state == ConcentrationState.concentrated
        assert "BIG" in result.flagged_tickers
        assert "SMALL" in result.flagged_tickers  # 0.3 > 0.25 too

    def test_role_over_40_percent_flagged(self):
        insights = [
            _insight("A", role=PortfolioRole.GROWTH_TECH),
            _insight("B", role=PortfolioRole.GROWTH_TECH),
            _insight("C", role=PortfolioRole.DEFENSIVE),
        ]
        insights[0].position = PositionContext(quantity=1.0, weight=0.25)
        insights[1].position = PositionContext(quantity=1.0, weight=0.25)
        insights[2].position = PositionContext(quantity=1.0, weight=0.5)

        result = evaluate_concentration(insights)

        assert "GROWTH_TECH" in result.flagged_roles  # 0.5 combined
        assert "DEFENSIVE" in result.flagged_roles  # 0.5 single role
        assert result.state == ConcentrationState.concentrated


class TestDetermineWeightedRisk:
    def test_high_when_risky_weight_over_half(self):
        insights = [
            _insight("A", state=AssetState.risky),
            _insight("B", state=AssetState.healthy),
        ]
        insights[0].position = PositionContext(quantity=1.0, weight=0.6)
        insights[1].position = PositionContext(quantity=1.0, weight=0.4)
        assert determine_weighted_risk(insights) == RiskLevel.high

    def test_medium_when_some_risky_weight(self):
        insights = [
            _insight("A", state=AssetState.unattractive),
            _insight("B", state=AssetState.healthy),
        ]
        insights[0].position = PositionContext(quantity=1.0, weight=0.1)
        insights[1].position = PositionContext(quantity=1.0, weight=0.9)
        assert determine_weighted_risk(insights) == RiskLevel.medium

    def test_low_when_no_risky_weight(self):
        insights = [_insight("A"), _insight("B")]
        insights[0].position = PositionContext(quantity=1.0, weight=0.5)
        insights[1].position = PositionContext(quantity=1.0, weight=0.5)
        assert determine_weighted_risk(insights) == RiskLevel.low

    def test_falls_back_to_counts_without_weights(self):
        insights = [
            _insight("A", state=AssetState.risky),
            _insight("B", state=AssetState.risky),
            _insight("C", state=AssetState.healthy),
        ]
        assert determine_weighted_risk(insights) == RiskLevel.high

    def test_small_risky_position_downgrades_vs_counts(self):
        """A tiny risky position should not dominate: counts say medium, and
        weighting keeps it medium — but a majority-count of tiny risky
        positions no longer forces high."""
        insights = [
            _insight("A", state=AssetState.risky),
            _insight("B", state=AssetState.risky),
            _insight("C", state=AssetState.healthy),
        ]
        insights[0].position = PositionContext(quantity=1.0, weight=0.05)
        insights[1].position = PositionContext(quantity=1.0, weight=0.05)
        insights[2].position = PositionContext(quantity=1.0, weight=0.9)
        assert determine_weighted_risk(insights) == RiskLevel.medium
