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
from insight_engine.rules.alternative_rules import filter_and_rank_candidates, should_trigger_alternatives
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
) -> Insight:
    """Resolve alternative suggestions after AI call (if applicable).

    If use_ai=True and AI returned suggestions, validates them with real metrics.
    Otherwise uses JSON config fallback candidates.
    """
    trigger_reasons = alternatives_context.get("trigger_reasons", [])
    role = insight.portfolio_role

    if sp500_hist is None:
        sp500_hist = market_data_provider.fetch_history("^GSPC", period="1y")

    # Check if AI provided suggestions
    ai_suggestions = getattr(insight, "_ai_suggestions", None)

    if use_ai and ai_suggestions:
        # Validate AI candidates with real metrics
        suggestions = _validate_ai_suggestions(
            ai_suggestions=ai_suggestions,
            user_profile=user_profile,
            market_data_provider=market_data_provider,
            exclude_ticker=insight.ticker,
            sp500_hist=sp500_hist,
        )
    else:
        # Fallback: use JSON config candidates
        suggestions = _get_fallback_suggestions(
            role=role,
            exclude_ticker=insight.ticker,
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
    exclude_ticker: str,
    sp500_hist=None,
) -> list[AlternativeSuggestion]:
    """Validate AI-suggested candidates with real metrics."""
    candidates_data = []

    for suggestion in ai_suggestions:
        if suggestion.ticker.upper() == exclude_ticker.upper():
            continue
        try:
            hist = market_data_provider.fetch_history(suggestion.ticker, period="1y")
            info = market_data_provider.fetch_info(suggestion.ticker)
            if sp500_hist is None:
                sp500_hist = market_data_provider.fetch_history("^GSPC", period="1y")

            from insight_engine.services.metrics import calculate_metrics
            metrics = calculate_metrics(hist, info, sp500_hist)
            dimensions = evaluate_dimensions(metrics)
            health = compute_health_score(dimensions, metrics)

            candidates_data.append({
                "ticker": suggestion.ticker,
                "health_score": health,
                "annualized_volatility": metrics.annualized_volatility,
                "max_drawdown": metrics.max_drawdown,
                "reason": suggestion.reason,
            })
        except Exception as e:
            logger.warning(f"Failed to validate AI candidate {suggestion.ticker}: {e}")
            continue

    ranked = filter_and_rank_candidates(candidates_data, user_profile, max_results=3)

    return [
        AlternativeSuggestion(
            ticker=c["ticker"],
            health_score=c["health_score"],
            reason=c.get("reason", ""),
        )
        for c in ranked
    ]


def _get_fallback_suggestions(
    role,
    exclude_ticker: str,
    user_profile: UserProfile,
    market_data_provider: MarketDataProvider,
    sp500_hist=None,
) -> list[AlternativeSuggestion]:
    """Fetch metrics for fallback candidates, score and filter them."""
    candidate_tickers = get_fallback_candidates(role, exclude_ticker)
    candidates_data = []

    for ticker in candidate_tickers:
        try:
            hist = market_data_provider.fetch_history(ticker, period="1y")
            info = market_data_provider.fetch_info(ticker)
            if sp500_hist is None:
                sp500_hist = market_data_provider.fetch_history("^GSPC", period="1y")

            from insight_engine.services.metrics import calculate_metrics
            metrics = calculate_metrics(hist, info, sp500_hist)
            dimensions = evaluate_dimensions(metrics)
            health = compute_health_score(dimensions, metrics)

            candidates_data.append({
                "ticker": ticker,
                "health_score": health,
                "annualized_volatility": metrics.annualized_volatility,
                "max_drawdown": metrics.max_drawdown,
                "reason": f"Similar role ({role.value}) with health score {health}/100",
            })
        except Exception as e:
            logger.warning(f"Failed to evaluate candidate {ticker}: {e}")
            continue

    ranked = filter_and_rank_candidates(candidates_data, user_profile, max_results=3)

    return [
        AlternativeSuggestion(
            ticker=c["ticker"],
            health_score=c["health_score"],
            reason=c.get("reason", ""),
        )
        for c in ranked
    ]
