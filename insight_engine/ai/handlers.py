import json
import logging

from insight_engine.ai.prompts import (
    BATCH_ALTERNATIVES_SECTION_TEMPLATE,
    BATCH_ASSET_BLOCK_TEMPLATE,
    BATCH_INSIGHT_PROMPT_TEMPLATE,
    INSIGHT_PROMPT_TEMPLATE,
    INSIGHT_WITH_ALTERNATIVES_PROMPT_TEMPLATE,
    PROFILE_INTERPRET_PROMPT_TEMPLATE,
    PROFILE_INTERPRET_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_user_context,
)
from insight_engine.config import settings
from insight_engine.domain.entities import Insight, UserProfile
from insight_engine.ports import LLMProvider

logger = logging.getLogger(__name__)


def generate_explanation(
    insight: Insight,
    user_profile: UserProfile | None = None,
    provider: LLMProvider | None = None,
    alternatives_context: dict | None = None,
) -> Insight:
    """Use an LLM to generate natural language explanation for an insight.

    Mutates and returns the insight with scenario, risks, and explanation filled in.
    When alternatives_context is provided, also requests alternative asset suggestions.
    """
    if not settings.openai_api_key:
        logger.warning("No OpenAI API key configured; skipping AI explanation")
        insight.scenario = "AI explanation unavailable (no API key configured)"
        insight.risks = _fallback_risks(insight)
        insight.explanation = "Configure OPENAI_API_KEY to enable natural language explanations."
        return insight

    if provider is None:
        from insight_engine.providers import get_llm_provider
        provider = get_llm_provider()

    user_context = build_user_context(user_profile)
    base_kwargs = dict(_asset_prompt_kwargs(insight), user_context=user_context)

    if alternatives_context:
        prompt = INSIGHT_WITH_ALTERNATIVES_PROMPT_TEMPLATE.format(
            **base_kwargs,
            health_score=alternatives_context.get("health_score", "N/A"),
            profile_fit_score=alternatives_context.get("profile_fit_score", "N/A"),
            portfolio_role=alternatives_context.get("portfolio_role", "N/A"),
            trigger_reasons=", ".join(alternatives_context.get("trigger_reasons", [])),
            news_flags_context=_news_flags_context(alternatives_context),
        )
    else:
        prompt = INSIGHT_PROMPT_TEMPLATE.format(**base_kwargs)

    try:
        content = provider.generate(SYSTEM_PROMPT, prompt)
        parsed = json.loads(content)
        _apply_parsed_explanation(insight, parsed, alternatives_context is not None)
    except Exception as e:
        logger.error(f"LLM provider error: {e}")
        _apply_error_fallback(insight)

    return insight


def generate_batch_explanations(
    items: list[tuple[Insight, dict | None]],
    user_profile: UserProfile | None = None,
    provider: LLMProvider | None = None,
    total_value: float | None = None,
    concentration=None,
) -> None:
    """Generate explanations for many insights with a single LLM call.

    items pairs each insight with its alternatives_context (or None).
    Mutates the insights in place; assets missing from the response get
    mechanical fallback text. total_value/concentration, when provided, give
    the model portfolio-level exposure context.
    """
    if not items:
        return

    if not settings.openai_api_key:
        logger.warning("No OpenAI API key configured; skipping AI explanation")
        for insight, _ in items:
            insight.scenario = "AI explanation unavailable (no API key configured)"
            insight.risks = _fallback_risks(insight)
            insight.explanation = (
                "Configure OPENAI_API_KEY to enable natural language explanations."
            )
        return

    if provider is None:
        from insight_engine.providers import get_llm_provider
        provider = get_llm_provider()

    blocks = []
    for insight, alternatives_context in items:
        alternatives_section = ""
        if alternatives_context:
            alternatives_section = BATCH_ALTERNATIVES_SECTION_TEMPLATE.format(
                health_score=alternatives_context.get("health_score", "N/A"),
                profile_fit_score=alternatives_context.get("profile_fit_score", "N/A"),
                portfolio_role=alternatives_context.get("portfolio_role", "N/A"),
                trigger_reasons=", ".join(alternatives_context.get("trigger_reasons", [])),
                news_flags_context=_news_flags_context(alternatives_context),
            )
        blocks.append(
            BATCH_ASSET_BLOCK_TEMPLATE.format(
                **_asset_prompt_kwargs(insight),
                position_context=_position_context_line(insight),
                alternatives_section=alternatives_section,
            )
        )

    prompt = BATCH_INSIGHT_PROMPT_TEMPLATE.format(
        user_context=build_user_context(user_profile),
        portfolio_context=_portfolio_context_line(total_value, concentration),
        asset_blocks="\n\n".join(blocks),
    )

    parsed: dict = {}
    try:
        # ~700 output tokens per asset: scenario, risks, explanation,
        # alternatives, plus JSON syntax/whitespace overhead. Capped below
        # gpt-4o-mini's 16k output limit.
        content = provider.generate(
            SYSTEM_PROMPT, prompt, max_tokens=min(16000, 700 * len(items) + 1000)
        )
        parsed = json.loads(content)
    except Exception as e:
        logger.error(f"LLM provider error: {e}")

    by_ticker = {
        key.upper(): value for key, value in parsed.items() if isinstance(value, dict)
    }
    for insight, alternatives_context in items:
        asset_parsed = by_ticker.get(insight.ticker.upper())
        if asset_parsed is None:
            _apply_error_fallback(insight)
        else:
            _apply_parsed_explanation(
                insight, asset_parsed, alternatives_context is not None
            )


class ProfileInterpretationError(Exception):
    """The LLM was unavailable or returned an invalid profile."""


_VALID_RISK = {"low", "moderate", "high"}
_VALID_HORIZON = {"short", "medium", "long"}
_VALID_GOAL = {"growth", "income", "capital_protection"}


def interpret_profile(text: str, provider: LLMProvider | None = None) -> dict:
    """Map a free-text description of investment wishes to a user profile.

    Returns {risk, horizon, goal, rationale} validated against the domain
    enums. Raises ProfileInterpretationError when no key is configured, the
    call fails, or the output doesn't validate — never guesses.
    """
    if not settings.openai_api_key:
        raise ProfileInterpretationError("No OpenAI API key configured")

    if provider is None:
        from insight_engine.providers import get_llm_provider
        provider = get_llm_provider()

    prompt = PROFILE_INTERPRET_PROMPT_TEMPLATE.format(text=text)
    try:
        content = provider.generate(
            PROFILE_INTERPRET_SYSTEM_PROMPT, prompt, temperature=0.0, max_tokens=300
        )
        parsed = json.loads(content)
    except Exception as e:
        logger.error(f"Profile interpretation error: {e}")
        raise ProfileInterpretationError("Could not interpret the description") from e

    risk = parsed.get("risk")
    horizon = parsed.get("horizon")
    goal = parsed.get("goal")
    if risk not in _VALID_RISK or horizon not in _VALID_HORIZON or goal not in _VALID_GOAL:
        logger.error(f"Profile interpretation returned invalid values: {parsed}")
        raise ProfileInterpretationError("Interpretation produced invalid profile values")

    return {
        "risk": risk,
        "horizon": horizon,
        "goal": goal,
        "rationale": str(parsed.get("rationale", "")),
    }


def _asset_prompt_kwargs(insight: Insight) -> dict:
    metrics = insight.metrics
    return dict(
        ticker=insight.ticker,
        asset_state=insight.asset_state.value,
        trend=insight.dimensions.trend.value,
        valuation=insight.dimensions.valuation.value,
        fundamentals=insight.dimensions.fundamentals.value,
        risk_level=insight.dimensions.risk_level.value,
        market_context=insight.dimensions.market_context.value,
        benchmark_ticker=insight.metrics.benchmark_ticker or "N/A",
        horizon=insight.horizon.value,
        current_price=_fmt(metrics.current_price),
        sma_50=_fmt(metrics.sma_50),
        sma_200=_fmt(metrics.sma_200),
        pe_ratio=_fmt(metrics.pe_ratio),
        revenue_growth=_pct(metrics.revenue_growth),
        profit_margin=_pct(metrics.profit_margin),
        debt_to_equity=_fmt(metrics.debt_to_equity),
        volatility=_pct(metrics.annualized_volatility),
        max_drawdown=_pct(metrics.max_drawdown),
    )


def _position_context_line(insight: Insight) -> str:
    position = getattr(insight, "position", None)
    if position is None:
        return ""
    parts = []
    if position.weight is not None:
        parts.append(f"{position.weight * 100:.1f}% of portfolio value")
    if position.unrealized_gain_pct is not None:
        direction = "gain" if position.unrealized_gain_pct >= 0 else "loss"
        parts.append(
            f"unrealized {direction} vs average cost: "
            f"{position.unrealized_gain_pct * 100:+.1f}%"
        )
    if not parts:
        return ""
    return f"Position Context: {'; '.join(parts)}\n"


def _portfolio_context_line(total_value: float | None, concentration) -> str:
    parts = []
    if total_value is not None:
        parts.append(f"total value {total_value:,.2f}")
    if concentration is not None:
        detail = concentration.state.value
        flags = concentration.flagged_tickers + concentration.flagged_roles
        if flags:
            detail += f" ({', '.join(flags)} above concentration thresholds)"
        parts.append(detail)
    if not parts:
        return ""
    return f"Portfolio Context: {'; '.join(parts)}"


def _news_flags_context(alternatives_context: dict) -> str:
    news_flags = alternatives_context.get("news_flags") or {}
    active_flags = [name for name, active in news_flags.items() if active]
    if not active_flags:
        return ""
    return f"- News Risk Flags: {', '.join(active_flags)}"


def _apply_parsed_explanation(
    insight: Insight, parsed: dict, expect_alternatives: bool
) -> None:
    insight.scenario = parsed.get("scenario", "")
    insight.risks = parsed.get("risks", [])[:3]
    insight.explanation = parsed.get("explanation", "")

    if expect_alternatives and "alternatives" in parsed:
        from insight_engine.domain.entities import AlternativeSuggestion
        ai_suggestions = [
            AlternativeSuggestion(
                ticker=alt.get("ticker", ""),
                reason=alt.get("reason", ""),
            )
            for alt in parsed["alternatives"][:5]
            if alt.get("ticker")
        ]
        # Store on insight for later merging with validated candidates
        insight._ai_suggestions = ai_suggestions


def _apply_error_fallback(insight: Insight) -> None:
    insight.scenario = "Unable to generate AI explanation at this time."
    insight.risks = _fallback_risks(insight)
    insight.explanation = ""


def _fallback_risks(insight: Insight) -> list[str]:
    """Generate mechanical risk list without AI."""
    from insight_engine.services.analysis import derive_risks
    return derive_risks(insight.dimensions, insight.metrics)


def _fmt(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"
