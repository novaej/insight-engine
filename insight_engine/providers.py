from insight_engine.adapters.azure_translator import AzureTranslatorProvider
from insight_engine.adapters.openai_llm import OpenAILLMProvider
from insight_engine.adapters.yahoo_finance import YahooFinanceProvider
from insight_engine.config import settings
from insight_engine.ports import LLMProvider, MarketDataProvider, TranslatorProvider


def get_llm_provider() -> LLMProvider:
    return OpenAILLMProvider(api_key=settings.openai_api_key, model=settings.openai_model)


def get_translator_provider() -> TranslatorProvider:
    return AzureTranslatorProvider(
        key=settings.azure_translator_key,
        endpoint=settings.azure_translator_endpoint,
        region=settings.azure_translator_region,
    )


def get_market_data_provider() -> MarketDataProvider:
    return YahooFinanceProvider()
