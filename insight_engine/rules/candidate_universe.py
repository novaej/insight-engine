import json
from pathlib import Path

from insight_engine.domain.enums import PortfolioRole

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "candidate_universe.json"
_candidates: dict[str, list[str]] | None = None


def load_candidates() -> dict[str, list[str]]:
    """Load the candidate universe from the JSON config file."""
    global _candidates
    if _candidates is None:
        with open(_CONFIG_PATH) as f:
            _candidates = json.load(f)
    return _candidates


def get_fallback_candidates(role: PortfolioRole, exclude_ticker: str) -> list[str]:
    """Get candidate tickers for a role, excluding the current asset."""
    candidates = load_candidates()
    tickers = candidates.get(role.value, [])
    return [t for t in tickers if t.upper() != exclude_ticker.upper()]
