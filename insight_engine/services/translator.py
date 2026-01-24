import logging

from insight_engine.config import settings
from insight_engine.ports import TranslatorProvider

logger = logging.getLogger(__name__)


def translate_texts(
    texts: list[str],
    target_language: str,
    provider: TranslatorProvider | None = None,
) -> list[str]:
    """Translate a list of texts to the target language.

    Returns the original texts unchanged if translation is unavailable or fails.
    """
    if not settings.azure_translator_key:
        logger.warning("No Azure Translator key configured; skipping translation")
        return texts

    if not texts:
        return texts

    if provider is None:
        from insight_engine.providers import get_translator_provider
        provider = get_translator_provider()

    try:
        return provider.translate(texts, target_language)
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return texts


def translate_insight(insight, target_language: str):
    """Translate the AI-generated fields of an Insight in place."""
    texts = [insight.scenario, insight.explanation] + insight.risks
    translated = translate_texts(texts, target_language)

    insight.scenario = translated[0]
    insight.explanation = translated[1]
    insight.risks = translated[2:]

    return insight
