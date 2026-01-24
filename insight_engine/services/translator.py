import logging
import uuid

import requests

from insight_engine.config import settings

logger = logging.getLogger(__name__)


def translate_texts(texts: list[str], target_language: str) -> list[str]:
    """Translate a list of texts to the target language using Azure Translator.

    Returns the original texts unchanged if translation is unavailable or fails.
    """
    if not settings.azure_translator_key:
        logger.warning("No Azure Translator key configured; skipping translation")
        return texts

    if not texts:
        return texts

    path = "/translate"
    url = settings.azure_translator_endpoint + path

    params = {
        "api-version": "3.0",
        "from": "en",
        "to": [target_language],
    }

    headers = {
        "Ocp-Apim-Subscription-Key": settings.azure_translator_key,
        "Ocp-Apim-Subscription-Region": settings.azure_translator_region,
        "Content-type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }

    body = [{"text": text} for text in texts]

    try:
        response = requests.post(url, params=params, headers=headers, json=body, timeout=10)
        response.raise_for_status()
        result = response.json()
        return [item["translations"][0]["text"] for item in result]
    except Exception as e:
        logger.error(f"Azure Translator error: {e}")
        return texts


def translate_insight(insight, target_language: str):
    """Translate the AI-generated fields of an Insight in place."""
    texts = [insight.scenario, insight.explanation] + insight.risks
    translated = translate_texts(texts, target_language)

    insight.scenario = translated[0]
    insight.explanation = translated[1]
    insight.risks = translated[2:]

    return insight
