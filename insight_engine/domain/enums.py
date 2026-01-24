from enum import Enum


class Trend(str, Enum):
    bullish = "bullish"
    sideways = "sideways"
    bearish = "bearish"


class Valuation(str, Enum):
    cheap = "cheap"
    reasonable = "reasonable"
    expensive = "expensive"
    inconclusive = "inconclusive"


class Fundamentals(str, Enum):
    strong = "strong"
    mixed = "mixed"
    weak = "weak"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class MarketContext(str, Enum):
    favorable = "favorable"
    adverse = "adverse"


class AssetState(str, Enum):
    healthy = "healthy"
    healthy_but_expensive = "healthy_but_expensive"
    neutral = "neutral"
    risky = "risky"
    unattractive = "unattractive"


class Horizon(str, Enum):
    short_term = "short_term"
    medium_term = "medium_term"
    long_term = "long_term"
    not_recommended = "not_recommended"


class AssetType(str, Enum):
    stock = "stock"
    etf = "etf"


class RiskProfile(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"


class InvestmentObjective(str, Enum):
    growth = "growth"
    income = "income"
    capital_protection = "capital_protection"


class PortfolioRole(str, Enum):
    US_LARGE_CAP_CORE = "US_LARGE_CAP_CORE"
    GROWTH_TECH = "GROWTH_TECH"
    DIVIDEND_INCOME = "DIVIDEND_INCOME"
    DEFENSIVE = "DEFENSIVE"
    EMERGING_MARKETS = "EMERGING_MARKETS"
    BONDS_STABILITY = "BONDS_STABILITY"
