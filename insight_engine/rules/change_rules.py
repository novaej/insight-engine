"""Deterministic change detection for the monitoring watchdog.

Compares a ticker's previous insight snapshot with a fresh one and reports
meaningful adverse transitions in plain language. Like all rules, it classifies
what changed; it never tells the user to act.
"""

from dataclasses import dataclass

from insight_engine.domain.enums import AssetState

HEALTH_DROP_THRESHOLD = 15

# Max-drawdown tolerance by risk profile (more negative = deeper loss allowed).
_DRAWDOWN_LIMIT = {"low": -0.15, "moderate": -0.25, "high": -0.35}

# Higher = healthier; a drop in rank is an adverse transition.
_STATE_RANK = {
    AssetState.healthy: 4,
    AssetState.healthy_but_expensive: 3,
    AssetState.neutral: 2,
    AssetState.risky: 1,
    AssetState.unattractive: 0,
}

_NEWS_LABELS = {
    "regulatory_risk": "regulatory risk",
    "earnings_negative": "negative earnings signals",
    "management_change": "a management change",
    "litigation_risk": "litigation risk",
}


@dataclass
class Snapshot:
    ticker: str
    asset_state: AssetState
    health_score: int | None = None
    current_price: float | None = None
    sma_200: float | None = None
    parabolic_sar: float | None = None
    max_drawdown: float | None = None
    news_flags: dict | None = None


@dataclass
class ChangeEvent:
    ticker: str
    kind: str
    message: str


def detect_changes(
    previous: Snapshot | None, current: Snapshot, risk: str
) -> list[ChangeEvent]:
    """Adverse transitions between the previous and current snapshot.

    No previous snapshot (first analysis of the ticker) → baseline, no events.
    """
    if previous is None:
        return []

    events: list[ChangeEvent] = []
    t = current.ticker

    # Asset state worsened
    prev_rank = _STATE_RANK.get(previous.asset_state)
    curr_rank = _STATE_RANK.get(current.asset_state)
    if prev_rank is not None and curr_rank is not None and curr_rank < prev_rank:
        events.append(
            ChangeEvent(
                t, "state_worsened",
                f"{t}: state changed {previous.asset_state.value} → "
                f"{current.asset_state.value}.",
            )
        )

    # Health score dropped sharply
    if previous.health_score is not None and current.health_score is not None:
        drop = previous.health_score - current.health_score
        if drop >= HEALTH_DROP_THRESHOLD:
            events.append(
                ChangeEvent(
                    t, "health_drop",
                    f"{t}: health score fell {previous.health_score} → "
                    f"{current.health_score}.",
                )
            )

    # Price crossed below its 200-day average
    if _crossed_below(previous.current_price, previous.sma_200,
                      current.current_price, current.sma_200):
        events.append(
            ChangeEvent(
                t, "sma200_cross_below",
                f"{t}: price crossed below its 200-day average.",
            )
        )

    # Parabolic SAR flipped from bullish to bearish
    if _crossed_below(previous.current_price, previous.parabolic_sar,
                      current.current_price, current.parabolic_sar):
        events.append(
            ChangeEvent(
                t, "sar_bearish",
                f"{t}: trend indicator (Parabolic SAR) turned bearish.",
            )
        )

    # Max drawdown newly breached the profile's tolerance
    limit = _DRAWDOWN_LIMIT.get(risk, -0.25)
    if (
        previous.max_drawdown is not None
        and current.max_drawdown is not None
        and previous.max_drawdown >= limit
        and current.max_drawdown < limit
    ):
        events.append(
            ChangeEvent(
                t, "drawdown_breach",
                f"{t}: maximum drawdown {current.max_drawdown * 100:.0f}% now "
                f"exceeds your {risk}-risk tolerance.",
            )
        )

    # A news flag became active since last run
    prev_news = previous.news_flags or {}
    curr_news = current.news_flags or {}
    for flag, label in _NEWS_LABELS.items():
        if curr_news.get(flag) and not prev_news.get(flag):
            events.append(
                ChangeEvent(t, f"news_{flag}", f"{t}: news now flags {label}.")
            )

    return events


def _crossed_below(prev_value, prev_ref, curr_value, curr_ref) -> bool:
    """True when value was at/above its reference before and is below it now."""
    if None in (prev_value, prev_ref, curr_value, curr_ref):
        return False
    return prev_value >= prev_ref and curr_value < curr_ref
