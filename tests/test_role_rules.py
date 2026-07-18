from insight_engine.domain.enums import PortfolioRole
from insight_engine.rules.role_rules import classify_role


class TestETFClassification:
    def test_bond_etf(self):
        info = {"quoteType": "ETF", "category": "Long-Term Bond", "fundFamily": "Vanguard"}
        assert classify_role(info) == PortfolioRole.BONDS_STABILITY

    def test_fixed_income_etf(self):
        info = {"quoteType": "ETF", "category": "Intermediate-Term Fixed Income"}
        assert classify_role(info) == PortfolioRole.BONDS_STABILITY

    def test_emerging_markets_etf(self):
        info = {"quoteType": "ETF", "category": "Diversified Emerging Mkts"}
        assert classify_role(info) == PortfolioRole.EMERGING_MARKETS

    def test_technology_etf(self):
        info = {"quoteType": "ETF", "category": "Technology"}
        assert classify_role(info) == PortfolioRole.GROWTH_TECH

    def test_growth_etf(self):
        info = {"quoteType": "ETF", "category": "Large Growth"}
        assert classify_role(info) == PortfolioRole.GROWTH_TECH

    def test_dividend_etf(self):
        info = {"quoteType": "ETF", "category": "High Dividend Yield"}
        assert classify_role(info) == PortfolioRole.DIVIDEND_INCOME

    def test_utilities_etf(self):
        info = {"quoteType": "ETF", "category": "Utilities"}
        assert classify_role(info) == PortfolioRole.DEFENSIVE

    def test_large_blend_etf(self):
        info = {"quoteType": "ETF", "category": "Large Blend"}
        assert classify_role(info) == PortfolioRole.US_LARGE_CAP_CORE

    def test_sp500_etf(self):
        info = {"quoteType": "ETF", "category": "S&P 500 Index"}
        assert classify_role(info) == PortfolioRole.US_LARGE_CAP_CORE

    def test_unknown_etf_with_vanguard(self):
        info = {"quoteType": "ETF", "category": "Some Unknown Category", "fundFamily": "Vanguard"}
        assert classify_role(info) == PortfolioRole.US_LARGE_CAP_CORE

    def test_unknown_etf_fallback(self):
        info = {"quoteType": "ETF", "category": "Weird Category", "fundFamily": "Unknown"}
        assert classify_role(info) == PortfolioRole.US_LARGE_CAP_CORE


class TestStockClassification:
    def test_tech_stock(self):
        info = {"quoteType": "EQUITY", "sector": "Technology", "marketCap": 2_000_000_000_000}
        assert classify_role(info) == PortfolioRole.GROWTH_TECH

    def test_communication_services_stock(self):
        info = {"quoteType": "EQUITY", "sector": "Communication Services", "marketCap": 500_000_000_000}
        assert classify_role(info) == PortfolioRole.GROWTH_TECH

    def test_utilities_stock(self):
        info = {"quoteType": "EQUITY", "sector": "Utilities", "marketCap": 50_000_000_000}
        assert classify_role(info) == PortfolioRole.DEFENSIVE

    def test_healthcare_stock(self):
        info = {"quoteType": "EQUITY", "sector": "Healthcare", "marketCap": 100_000_000_000}
        assert classify_role(info) == PortfolioRole.DEFENSIVE

    def test_consumer_defensive_stock(self):
        info = {"quoteType": "EQUITY", "sector": "Consumer Defensive", "marketCap": 80_000_000_000}
        assert classify_role(info) == PortfolioRole.DEFENSIVE

    def test_high_dividend_stock(self):
        # 5% yield expressed as a fraction (trailingAnnualDividendYield)
        info = {"quoteType": "EQUITY", "sector": "Energy", "marketCap": 200_000_000_000,
                "trailingAnnualDividendYield": 0.05}
        assert classify_role(info) == PortfolioRole.DIVIDEND_INCOME

    def test_high_dividend_stock_percent_units(self):
        # yfinance dividendYield as a percent (5.0 = 5%) still classifies correctly
        info = {"quoteType": "EQUITY", "sector": "Energy", "marketCap": 200_000_000_000,
                "dividendYield": 5.0}
        assert classify_role(info) == PortfolioRole.DIVIDEND_INCOME

    def test_low_yield_stock_not_dividend_income(self):
        # A tiny yield (0.3%) must NOT trip DIVIDEND_INCOME (the percent/fraction bug)
        info = {"quoteType": "EQUITY", "sector": "Energy", "marketCap": 200_000_000_000,
                "dividendYield": 0.3}
        assert classify_role(info) == PortfolioRole.US_LARGE_CAP_CORE

    def test_large_cap_stock(self):
        info = {"quoteType": "EQUITY", "sector": "Industrials", "marketCap": 100_000_000_000}
        assert classify_role(info) == PortfolioRole.US_LARGE_CAP_CORE

    def test_small_cap_stock_fallback(self):
        info = {"quoteType": "EQUITY", "sector": "Industrials", "marketCap": 5_000_000_000}
        assert classify_role(info) == PortfolioRole.US_LARGE_CAP_CORE

    def test_missing_fields_fallback(self):
        info = {"quoteType": "EQUITY"}
        assert classify_role(info) == PortfolioRole.US_LARGE_CAP_CORE
