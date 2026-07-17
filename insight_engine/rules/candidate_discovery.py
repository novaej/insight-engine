"""Dynamic alternative-candidate discovery from role-benchmark ETF holdings.

Widens the fixed candidate universe with the live top holdings of each role's
benchmark ETF (e.g. GROWTH_TECH → QQQ's holdings), then hands the union to the
same validation chain used for the static list. Discovery augments the curated
universe; it never replaces it, so roles without a usable ETF (bonds, emerging
markets) and any fetch failure still work.
"""

import json
import re
from pathlib import Path

from insight_engine.domain.enums import PortfolioRole
from insight_engine.ports import MarketDataProvider
from insight_engine.rules.candidate_universe import get_fallback_candidates

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "discovery_etfs.json"
_discovery_etfs: dict[str, str] | None = None

# US-listed common-stock symbols only; drops foreign listings like 2330.TW.
_US_TICKER = re.compile(r"^[A-Z]{1,5}$")


def load_discovery_etfs() -> dict[str, str]:
    global _discovery_etfs
    if _discovery_etfs is None:
        with open(_CONFIG_PATH) as f:
            _discovery_etfs = json.load(f)
    return _discovery_etfs


def get_discovery_etf(role: PortfolioRole | None) -> str | None:
    """The ETF whose holdings seed candidate discovery for a role, or None."""
    if role is None:
        return None
    return load_discovery_etfs().get(role.value)


def discover_candidates(
    role: PortfolioRole | None, market_data_provider: MarketDataProvider
) -> list[str]:
    """Union of the role's benchmark-ETF holdings and the static candidate list.

    Discovered tickers come first (fresher), then any static-only extras.
    Returns just the static list if the role has no discovery ETF or the
    holdings fetch fails / is empty.
    """
    static = get_fallback_candidates(role, "")
    etf = get_discovery_etf(role)
    if etf is None:
        return static

    try:
        holdings = market_data_provider.fetch_holdings(etf)
    except Exception:
        holdings = []

    discovered = [
        t.upper()
        for t in holdings
        if _US_TICKER.match(t.upper()) and t.upper() != etf.upper()
    ]

    seen: set[str] = set()
    ordered: list[str] = []
    for ticker in [*discovered, *static]:
        key = ticker.upper()
        if key not in seen:
            seen.add(key)
            ordered.append(ticker)
    return ordered
