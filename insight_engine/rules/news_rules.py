from insight_engine.domain.entities import NewsFlags


# Keyword sets for each risk flag
_REGULATORY_KEYWORDS = [
    "regulatory", "regulation", "sec", "antitrust", "fine", "fined",
    "compliance", "sanctions", "investigation", "probe", "subpoena",
]

_EARNINGS_NEGATIVE_KEYWORDS = [
    "misses", "missed", "disappoints", "downgrade", "loss", "losses",
    "decline", "slump", "warning", "profit warning", "revenue miss",
    "below expectations", "guidance cut",
]

_MANAGEMENT_KEYWORDS = [
    "ceo resign", "ceo steps down", "ceo fired", "ceo departure",
    "cfo resign", "cfo steps down", "management shakeup", "executive leaves",
    "leadership change", "board ousts",
]

_LITIGATION_KEYWORDS = [
    "lawsuit", "sued", "litigation", "class action", "settlement",
    "legal action", "court ruling", "damages", "plaintiff", "defendant",
]


def extract_news_flags(news_items: list[dict]) -> NewsFlags:
    """Extract binary risk flags from news headlines via keyword matching.

    Each news_item should have a 'title' key with the headline text.
    """
    if not news_items:
        return NewsFlags()

    # Combine all titles into one lowercased string for efficient matching
    combined = " ".join(
        (item.get("title") or "").lower() for item in news_items
    )

    return NewsFlags(
        regulatory_risk=any(kw in combined for kw in _REGULATORY_KEYWORDS),
        earnings_negative=any(kw in combined for kw in _EARNINGS_NEGATIVE_KEYWORDS),
        management_change=any(kw in combined for kw in _MANAGEMENT_KEYWORDS),
        litigation_risk=any(kw in combined for kw in _LITIGATION_KEYWORDS),
    )
