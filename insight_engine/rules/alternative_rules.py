from insight_engine.domain.entities import AssetScores, NewsFlags, UserProfile


def should_trigger_alternatives(
    scores: AssetScores, news_flags: NewsFlags | None = None
) -> tuple[bool, list[str]]:
    """Determine if alternatives should be suggested.

    Returns (triggered, list_of_reasons).
    """
    reasons: list[str] = []

    if scores.health_score < 50:
        reasons.append(f"Low health score ({scores.health_score}/100)")
    if scores.profile_fit_score < 50:
        reasons.append(f"Low profile fit score ({scores.profile_fit_score}/100)")

    if news_flags:
        if news_flags.regulatory_risk:
            reasons.append("Regulatory risk detected in news")
        if news_flags.earnings_negative:
            reasons.append("Negative earnings signals in news")
        if news_flags.management_change:
            reasons.append("Management change detected in news")
        if news_flags.litigation_risk:
            reasons.append("Litigation risk detected in news")

    return (len(reasons) > 0, reasons)


def filter_and_rank_candidates(
    candidates_data: list[dict],
    user_profile: UserProfile,
    max_results: int = 3,
) -> list[dict]:
    """Filter candidates by risk tolerance and rank by health score.

    Each candidate_data dict should have:
      - ticker: str
      - annualized_volatility: float | None
      - max_drawdown: float | None
      - health_score: int
      - reason: str (optional)
    """
    risk = user_profile.risk.value

    # Volatility tolerance thresholds (as decimal)
    vol_thresholds = {"low": 0.15, "moderate": 0.25, "high": 0.40}
    vol_limit = vol_thresholds.get(risk, 0.25)

    # Drawdown tolerance thresholds
    dd_thresholds = {"low": -0.10, "moderate": -0.20, "high": -0.35}
    dd_limit = dd_thresholds.get(risk, -0.20)

    filtered = []
    for c in candidates_data:
        vol = c.get("annualized_volatility")
        dd = c.get("max_drawdown")

        # Hard filters: exclude if exceeds tolerance
        if vol is not None and vol > vol_limit:
            continue
        if dd is not None and dd < dd_limit:
            continue

        filtered.append(c)

    # Rank by health_score descending
    filtered.sort(key=lambda x: x.get("health_score", 0), reverse=True)

    return filtered[:max_results]
