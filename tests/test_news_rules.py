from insight_engine.rules.news_rules import extract_news_flags


class TestExtractNewsFlags:
    def test_empty_news_returns_all_false(self):
        flags = extract_news_flags([])
        assert flags.regulatory_risk is False
        assert flags.earnings_negative is False
        assert flags.management_change is False
        assert flags.litigation_risk is False

    def test_regulatory_keywords(self):
        news = [{"title": "SEC investigation into company practices"}]
        flags = extract_news_flags(news)
        assert flags.regulatory_risk is True
        assert flags.earnings_negative is False

    def test_antitrust_keyword(self):
        news = [{"title": "Antitrust probe launched by regulators"}]
        flags = extract_news_flags(news)
        assert flags.regulatory_risk is True

    def test_sanctions_keyword(self):
        news = [{"title": "Company faces new sanctions from government"}]
        flags = extract_news_flags(news)
        assert flags.regulatory_risk is True

    def test_earnings_negative_misses(self):
        news = [{"title": "Company misses earnings expectations in Q3"}]
        flags = extract_news_flags(news)
        assert flags.earnings_negative is True

    def test_earnings_negative_downgrade(self):
        news = [{"title": "Analyst downgrade sends stock lower"}]
        flags = extract_news_flags(news)
        assert flags.earnings_negative is True

    def test_earnings_negative_guidance_cut(self):
        news = [{"title": "Company issues guidance cut for next quarter"}]
        flags = extract_news_flags(news)
        assert flags.earnings_negative is True

    def test_management_change_ceo_resign(self):
        news = [{"title": "CEO resigns amid corporate restructuring"}]
        flags = extract_news_flags(news)
        assert flags.management_change is True

    def test_management_shakeup(self):
        news = [{"title": "Management shakeup at major tech firm"}]
        flags = extract_news_flags(news)
        assert flags.management_change is True

    def test_litigation_lawsuit(self):
        news = [{"title": "Company faces major lawsuit from investors"}]
        flags = extract_news_flags(news)
        assert flags.litigation_risk is True

    def test_litigation_class_action(self):
        news = [{"title": "Class action filed against pharmaceutical company"}]
        flags = extract_news_flags(news)
        assert flags.litigation_risk is True

    def test_litigation_settlement(self):
        news = [{"title": "Company agrees to settlement in fraud case"}]
        flags = extract_news_flags(news)
        assert flags.litigation_risk is True

    def test_multiple_flags_from_multiple_articles(self):
        news = [
            {"title": "SEC investigation opens"},
            {"title": "Company misses revenue expectations"},
            {"title": "CEO steps down effective immediately"},
        ]
        flags = extract_news_flags(news)
        assert flags.regulatory_risk is True
        assert flags.earnings_negative is True
        assert flags.management_change is True
        assert flags.litigation_risk is False

    def test_no_matching_keywords(self):
        news = [
            {"title": "Company announces new product line"},
            {"title": "Stock hits all-time high"},
        ]
        flags = extract_news_flags(news)
        assert flags.regulatory_risk is False
        assert flags.earnings_negative is False
        assert flags.management_change is False
        assert flags.litigation_risk is False

    def test_case_insensitive_matching(self):
        news = [{"title": "SEC INVESTIGATION Into Company"}]
        flags = extract_news_flags(news)
        assert flags.regulatory_risk is True

    def test_missing_title_handled(self):
        news = [{"title": None}, {}]
        flags = extract_news_flags(news)
        assert flags.regulatory_risk is False
