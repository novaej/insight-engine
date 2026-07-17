import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAILLMProvider:
    def __init__(self, api_key: str, model: str):
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        choice = response.choices[0]
        if choice.finish_reason == "length":
            logger.warning(
                f"LLM output truncated at max_tokens={max_tokens}; "
                "the JSON response will likely be unparseable"
            )
        return choice.message.content
