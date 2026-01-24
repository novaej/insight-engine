from pydantic import BaseModel, Field

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


class UserProfileRequest(BaseModel):
    risk: RiskProfile = RiskProfile.moderate
    horizon: str = "long"
    goal: InvestmentObjective = InvestmentObjective.growth


class AnalyzeAssetRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    user_profile: UserProfileRequest | None = None
    use_ai: bool = True


class DimensionsResponse(BaseModel):
    trend: Trend
    valuation: Valuation
    fundamentals: Fundamentals
    risk_level: RiskLevel
    market_context: MarketContext


class MetricsResponse(BaseModel):
    current_price: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    pe_ratio: float | None = None
    revenue_growth: float | None = None
    profit_margin: float | None = None
    debt_to_equity: float | None = None
    annualized_volatility: float | None = None
    max_drawdown: float | None = None


class InsightResponse(BaseModel):
    ticker: str
    asset_state: AssetState
    dimensions: DimensionsResponse
    metrics: MetricsResponse
    horizon: Horizon
    scenario: str
    risks: list[str]
    explanation: str


class PortfolioAsset(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)


class PortfolioRequest(BaseModel):
    user_profile: UserProfileRequest
    assets: list[PortfolioAsset] = Field(..., min_length=1, max_length=20)
    use_ai: bool = True


class PortfolioSummaryResponse(BaseModel):
    total_assets: int
    insights: list[InsightResponse]
    overall_risk: RiskLevel
    summary: str
