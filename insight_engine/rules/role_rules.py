from insight_engine.domain.enums import PortfolioRole


def classify_role(info: dict) -> PortfolioRole:
    """Classify an asset's portfolio role from its info dict."""
    quote_type = info.get("quoteType", "").upper()

    if quote_type == "ETF":
        return _classify_etf(info)
    return _classify_stock(info)


def _classify_etf(info: dict) -> PortfolioRole:
    category = (info.get("category") or "").lower()
    fund_family = (info.get("fundFamily") or "").lower()

    if any(kw in category for kw in ["bond", "fixed income", "treasury"]):
        return PortfolioRole.BONDS_STABILITY
    if any(kw in category for kw in ["emerging", "developing"]):
        return PortfolioRole.EMERGING_MARKETS
    if any(kw in category for kw in ["technology", "growth"]):
        return PortfolioRole.GROWTH_TECH
    if any(kw in category for kw in ["dividend", "income", "yield"]):
        return PortfolioRole.DIVIDEND_INCOME
    if any(kw in category for kw in ["utilities", "consumer defensive", "health"]):
        return PortfolioRole.DEFENSIVE
    if any(kw in category for kw in ["large blend", "large cap", "s&p 500"]):
        return PortfolioRole.US_LARGE_CAP_CORE

    # Fallback heuristics on fund family
    if any(kw in fund_family for kw in ["vanguard", "ishares", "spdr"]):
        return PortfolioRole.US_LARGE_CAP_CORE

    return PortfolioRole.US_LARGE_CAP_CORE


def _classify_stock(info: dict) -> PortfolioRole:
    from insight_engine.services.metrics import normalize_dividend_yield

    sector = (info.get("sector") or "").lower()
    market_cap = info.get("marketCap") or 0
    dividend_yield = normalize_dividend_yield(info) or 0  # fraction, unit-safe

    if sector in ("technology", "communication services"):
        return PortfolioRole.GROWTH_TECH
    if sector in ("utilities", "consumer defensive", "healthcare"):
        return PortfolioRole.DEFENSIVE
    if dividend_yield > 0.03:
        return PortfolioRole.DIVIDEND_INCOME
    if market_cap > 50_000_000_000:
        return PortfolioRole.US_LARGE_CAP_CORE

    return PortfolioRole.US_LARGE_CAP_CORE
