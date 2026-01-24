from dataclasses import dataclass, field

from insight_engine.domain.enums import (
    AssetState,
    Fundamentals,
    Horizon,
    InvestmentObjective,
    MarketContext,
    RiskLevel,
    RiskProfile,
    Trend,
    Valuation,
)


@dataclass
class UserProfile:
    risk: RiskProfile
    horizon: str  # short, medium, long
    objective: InvestmentObjective


@dataclass
class DimensionResults:
    trend: Trend
    valuation: Valuation
    fundamentals: Fundamentals
    risk_level: RiskLevel
    market_context: MarketContext


@dataclass
class MetricsSummary:
    sma_50: float | None = None
    sma_200: float | None = None
    current_price: float | None = None
    pe_ratio: float | None = None
    pe_historical_avg: float | None = None
    revenue_growth: float | None = None
    profit_margin: float | None = None
    debt_to_equity: float | None = None
    max_drawdown: float | None = None
    annualized_volatility: float | None = None
    sp500_above_sma200: bool | None = None
    parabolic_sar: float | None = None


@dataclass
class Insight:
    ticker: str
    asset_state: AssetState
    dimensions: DimensionResults
    metrics: MetricsSummary
    horizon: Horizon
    scenario: str = ""
    risks: list[str] = field(default_factory=list)
    explanation: str = ""
