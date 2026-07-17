import logging

from insight_engine.domain.entities import (
    AlternativesResult,
    AlternativeSuggestion,
    AssetScores,
    Insight,
    NewsFlags,
    UserProfile,
)
from insight_engine.ports import MarketDataProvider
from insight_engine.rules.alternative_rules import (
    filter_and_rank_candidates,
    should_trigger_alternatives,
)
from insight_engine.rules.candidate_universe import get_fallback_candidates
from insight_engine.rules.news_rules import extract_news_flags
from insight_engine.rules.role_rules import classify_role
from insight_engine.rules.scoring_rules import compute_health_score, compute_profile_fit_score
from insight_engine.services.analysis import evaluate_dimensions

logger = logging.getLogger(__name__)


def prepare_alternatives_context(
    insight: Insight,
    info: dict,
    user_profile: UserProfile,
    market_data_provider: MarketDataProvider,
) -> dict | None:
    """Compute scores, role, news flags, and check if alternatives should trigger.

    Mutates insight with portfolio_role, scores, and news_flags.
    Returns alternatives_context dict if triggered, None otherwise.
    """
    # 1. Classify role
    role = classify_role(info)
    insight.portfolio_role = role

    # 2. Compute scores
    health = compute_health_score(insight.dimensions, insight.metrics)
    fit = compute_profile_fit_score(insight.metrics, insight.dimensions, user_profile)
    insight.scores = AssetScores(health_score=health, profile_fit_score=fit)

    # 3. Fetch news and extract flags
    try:
        news_items = market_data_provider.fetch_news(insight.ticker)
        news_flags = extract_news_flags(news_items)
    except Exception as e:
        logger.warning(f"Failed to fetch news for {insight.ticker}: {e}")
        news_flags = NewsFlags()
    insight.news_flags = news_flags

    # 4. Check trigger
    triggered, reasons = should_trigger_alternatives(insight.scores, news_flags)
    if not triggered:
        insight.alternatives = AlternativesResult(triggered=False)
        return None

    return {
        "health_score": health,
        "profile_fit_score": fit,
        "portfolio_role": role.value,
        "trigger_reasons": reasons,
        "news_flags": {
            "regulatory_risk": news_flags.regulatory_risk,
            "earnings_negative": news_flags.earnings_negative,
            "management_change": news_flags.management_change,
            "litigation_risk": news_flags.litigation_risk,
        },
    }


def resolve_alternatives(
    insight: Insight,
    user_profile: UserProfile,
    market_data_provider: MarketDataProvider,
    alternatives_context: dict,
    use_ai: bool = True,
    sp500_hist=None,
    held_tickers: set[str] | None = None,
) -> Insight:
    """Resolve alternative suggestions after AI call (if applicable).

    AI-proposed candidates are validated with real metrics first; if none
    survive filtering (risk tolerance + profile fit), the JSON config
    candidates are tried as a fallback. Tickers already held in the portfolio
    are never suggested.
    """
    trigger_reasons = alternatives_context.get("trigger_reasons", [])
    role = insight.portfolio_role

    if sp500_hist is None:
        sp500_hist = market_data_provider.fetch_history("^GSPC", period="1y")

    exclude = {insight.ticker.upper()}
    if held_tickers:
        exclude |= {t.upper() for t in held_tickers}

    # Check if AI provided suggestions
    ai_suggestions = getattr(insight, "_ai_suggestions", None)

    suggestions = []
    if use_ai and ai_suggestions:
        # Validate AI candidates with real metrics
        suggestions = _validate_ai_suggestions(
            ai_suggestions=ai_suggestions,
            user_profile=user_profile,
            market_data_provider=market_data_provider,
            exclude_tickers=exclude,
            sp500_hist=sp500_hist,
        )
    if not suggestions:
        # Fallback: use JSON config candidates (also when AI candidates were
        # all filtered out)
        suggestions = _get_fallback_suggestions(
            role=role,
            exclude_tickers=exclude,
            user_profile=user_profile,
            market_data_provider=market_data_provider,
            sp500_hist=sp500_hist,
        )

    insight.alternatives = AlternativesResult(
        triggered=True,
        trigger_reasons=trigger_reasons,
        suggestions=suggestions,
    )

    # Clean up temporary attribute
    if hasattr(insight, "_ai_suggestions"):
        del insight._ai_suggestions

    return insight


def _validate_ai_suggestions(
    ai_suggestions: list[AlternativeSuggestion],
    user_profile: UserProfile,
    market_data_provider: MarketDataProvider,
    exclude_tickers: set[str],
    sp500_hist=None,
) -> list[AlternativeSuggestion]:
    """Validate AI-suggested candidates with real metrics."""
    candidates_data = []

    for suggestion in ai_suggestions:
        if suggestion.ticker.upper() in exclude_tickers:
            continue
        candidate = _evaluate_candidate(
            suggestion.ticker,
            user_profile,
            market_data_provider,
            sp500_hist,
            reason=suggestion.reason,
        )
        if candidate is not None:
            candidates_data.append(candidate)

    ranked = filter_and_rank_candidates(candidates_data, user_profile, max_results=3)
    return [_to_suggestion(c) for c in ranked]


def _get_fallback_suggestions(
    role,
    exclude_tickers: set[str],
    user_profile: UserProfile,
    market_data_provider: MarketDataProvider,
    sp500_hist=None,
) -> list[AlternativeSuggestion]:
    """Fetch metrics for fallback candidates, score and filter them."""
    candidate_tickers = get_fallback_candidates(role, "")
    candidates_data = []

    for ticker in candidate_tickers:
        if ticker.upper() in exclude_tickers:
            continue
        candidate = _evaluate_candidate(
            ticker, user_profile, market_data_provider, sp500_hist
        )
        if candidate is not None:
            candidate["reason"] = (
                f"Similar role ({role.value}) with health score "
                f"{candidate['health_score']}/100"
            )
            candidates_data.append(candidate)

    ranked = filter_and_rank_candidates(candidates_data, user_profile, max_results=3)
    return [_to_suggestion(c) for c in ranked]


def _evaluate_candidate(
    ticker: str,
    user_profile: UserProfile,
    market_data_provider: MarketDataProvider,
    sp500_hist=None,
    reason: str = "",
) -> dict | None:
    """Fetch real metrics for a candidate and score it (health + profile fit)."""
    try:
        hist = market_data_provider.fetch_history(ticker, period="1y")
        info = market_data_provider.fetch_info(ticker)
        if sp500_hist is None:
            sp500_hist = market_data_provider.fetch_history("^GSPC", period="1y")

        from insight_engine.services.metrics import calculate_metrics
        metrics = calculate_metrics(hist, info, sp500_hist)
        dimensions = evaluate_dimensions(metrics)

        return {
            "ticker": ticker,
            "health_score": compute_health_score(dimensions, metrics),
            "profile_fit_score": compute_profile_fit_score(
                metrics, dimensions, user_profile
            ),
            "annualized_volatility": metrics.annualized_volatility,
            "max_drawdown": metrics.max_drawdown,
            "reason": reason,
        }
    except Exception as e:
        logger.warning(f"Failed to evaluate candidate {ticker}: {e}")
        return None


def _to_suggestion(candidate: dict) -> AlternativeSuggestion:
    return AlternativeSuggestion(
        ticker=candidate["ticker"],
        health_score=candidate["health_score"],
        profile_fit_score=candidate.get("profile_fit_score"),
        reason=candidate.get("reason", ""),
    )
