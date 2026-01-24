import json
import logging

from insight_engine.ai.prompts import INSIGHT_PROMPT_TEMPLATE, SYSTEM_PROMPT, build_user_context
from insight_engine.config import settings
from insight_engine.domain.entities import Insight, UserProfile
from insight_engine.ports import LLMProvider

logger = logging.getLogger(__name__)


def generate_explanation(
    insight: Insight,
    user_profile: UserProfile | None = None,
    provider: LLMProvider | None = None,
) -> Insight:
    """Use an LLM to generate natural language explanation for an insight.

    Mutates and returns the insight with scenario, risks, and explanation filled in.
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
    metrics = insight.metrics

    prompt = INSIGHT_PROMPT_TEMPLATE.format(
        ticker=insight.ticker,
        asset_state=insight.asset_state.value,
        trend=insight.dimensions.trend.value,
        valuation=insight.dimensions.valuation.value,
        fundamentals=insight.dimensions.fundamentals.value,
        risk_level=insight.dimensions.risk_level.value,
        market_context=insight.dimensions.market_context.value,
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
        user_context=user_context,
    )

    try:
        content = provider.generate(SYSTEM_PROMPT, prompt)
        parsed = json.loads(content)

        insight.scenario = parsed.get("scenario", "")
        insight.risks = parsed.get("risks", [])[:3]
        insight.explanation = parsed.get("explanation", "")
    except Exception as e:
        logger.error(f"LLM provider error: {e}")
        insight.scenario = "Unable to generate AI explanation at this time."
        insight.risks = _fallback_risks(insight)
        insight.explanation = ""

    return insight


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
