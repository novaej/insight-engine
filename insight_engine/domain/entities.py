from dataclasses import dataclass, field

from insight_engine.domain.enums import (
    AssetState,
    Fundamentals,
    Horizon,
    InvestmentObjective,
    MarketContext,
    PortfolioRole,
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
class AssetScores:
    health_score: int
    profile_fit_score: int


@dataclass
class NewsFlags:
    regulatory_risk: bool = False
    earnings_negative: bool = False
    management_change: bool = False
    litigation_risk: bool = False


@dataclass
class AlternativeSuggestion:
    ticker: str
    health_score: int | None = None
    reason: str = ""


@dataclass
class AlternativesResult:
    triggered: bool
    trigger_reasons: list[str] = field(default_factory=list)
    suggestions: list[AlternativeSuggestion] = field(default_factory=list)


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
    portfolio_role: PortfolioRole | None = None
    scores: AssetScores | None = None
    news_flags: NewsFlags | None = None
    alternatives: AlternativesResult | None = None
