from typing import Protocol

import pandas as pd


class LLMProvider(Protocol):
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str: ...


class TranslatorProvider(Protocol):
    def translate(self, texts: list[str], target_language: str) -> list[str]: ...


class MarketDataProvider(Protocol):
    def fetch_history(self, ticker: str, period: str = "2y") -> pd.DataFrame: ...

    def fetch_info(self, ticker: str) -> dict: ...

    def fetch_news(self, ticker: str) -> list[dict]: ...

    def fetch_holdings(self, etf_ticker: str) -> list[str]: ...


class EmailProvider(Protocol):
    def send(
        self, to: str, subject: str, text: str, html: str | None = None
    ) -> bool: ...
