import datetime

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
    UserHorizon,
    Valuation,
)

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserProfileRequest(BaseModel):
    risk: RiskProfile = RiskProfile.moderate
    horizon: UserHorizon = UserHorizon.long
    goal: InvestmentObjective = InvestmentObjective.growth


class ProfileInterpretRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Plain-words description of what you want from your investments",
    )


class ProfileInterpretResponse(BaseModel):
    risk: RiskProfile
    horizon: UserHorizon
    goal: InvestmentObjective
    rationale: str = ""


class UserCreateRequest(BaseModel):
    email: str = Field(..., max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8, max_length=128)
    name: str | None = Field(None, max_length=100)


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None = None


class UserUpdateRequest(BaseModel):
    email: str | None = Field(None, max_length=255, pattern=EMAIL_PATTERN)
    name: str | None = Field(None, max_length=100)
    password: str | None = Field(None, min_length=8, max_length=128)
    current_password: str | None = Field(
        None, description="Required when changing the password"
    )


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"


class AnalyzeAssetRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    user_profile: UserProfileRequest | None = None
    use_ai: bool = True
    language: str | None = Field(None, min_length=2, max_length=10, description="Target language code (e.g. 'es', 'fr', 'pt')")


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
    parabolic_sar: float | None = None
    pe_ratio: float | None = None
    revenue_growth: float | None = None
    profit_margin: float | None = None
    debt_to_equity: float | None = None
    annualized_volatility: float | None = None
    max_drawdown: float | None = None


class AlternativeResponse(BaseModel):
    ticker: str
    health_score: int | None = None
    reason: str = ""


class AlternativesResponse(BaseModel):
    triggered: bool
    trigger_reasons: list[str] = []
    suggestions: list[AlternativeResponse] = []


class PositionContextResponse(BaseModel):
    quantity: float
    market_value: float | None = None
    weight: float | None = None
    avg_purchase_price: float | None = None
    unrealized_gain_pct: float | None = None


class ConcentrationResponse(BaseModel):
    state: str
    flagged_tickers: list[str] = []
    flagged_roles: list[str] = []


class InsightResponse(BaseModel):
    ticker: str
    asset_state: AssetState
    dimensions: DimensionsResponse
    metrics: MetricsResponse
    horizon: Horizon
    scenario: str
    risks: list[str]
    explanation: str
    portfolio_role: str | None = None
    health_score: int | None = None
    profile_fit_score: int | None = None
    alternatives: AlternativesResponse | None = None
    analyzed_at: datetime.datetime | None = None
    position: PositionContextResponse | None = None


class PortfolioAsset(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)
    purchase_price: float | None = Field(None, gt=0)
    purchase_date: datetime.date | None = None


class PositionResponse(BaseModel):
    id: int | None = None
    ticker: str
    quantity: float
    purchase_price: float | None = None
    purchase_date: datetime.date | None = None
    updated_at: datetime.datetime | None = None


class PositionUpdateRequest(BaseModel):
    quantity: float | None = Field(None, gt=0)
    purchase_price: float | None = Field(None, gt=0)
    purchase_date: datetime.date | None = None


class PortfolioRequest(BaseModel):
    user_profile: UserProfileRequest
    assets: list[PortfolioAsset] | None = Field(
        None,
        min_length=1,
        max_length=100,
        description=(
            "Omit to analyze the stored positions. Entries with the same ticker "
            "are separate lots; max 20 distinct tickers."
        ),
    )
    use_ai: bool = True
    language: str | None = Field(None, min_length=2, max_length=10, description="Target language code (e.g. 'es', 'fr', 'pt')")


class PortfolioUpdateRequest(BaseModel):
    user_profile: UserProfileRequest | None = None
    assets: list[PortfolioAsset] = Field(..., min_length=1, max_length=100)
    use_ai: bool = True
    language: str | None = Field(None, min_length=2, max_length=10, description="Target language code (e.g. 'es', 'fr', 'pt')")


class PortfolioSummaryResponse(BaseModel):
    total_assets: int
    insights: list[InsightResponse]
    overall_risk: RiskLevel
    summary: str
    total_value: float | None = None
    concentration: ConcentrationResponse | None = None


class PortfolioResponse(BaseModel):
    id: int
    user_profile: UserProfileRequest
    assets: list[PositionResponse]
    overall_risk: RiskLevel
    summary: str
    insights: list[InsightResponse]
    updated_at: datetime.datetime
    total_value: float | None = None
    concentration: ConcentrationResponse | None = None


class InsightHistoryResponse(BaseModel):
    total: int
    insights: list[InsightResponse]
