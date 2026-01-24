import uuid

import requests


class AzureTranslatorProvider:
    def __init__(self, key: str, endpoint: str, region: str):
        self._key = key
        self._endpoint = endpoint
        self._region = region

    def translate(self, texts: list[str], target_language: str) -> list[str]:
        url = self._endpoint + "/translate"

        params = {
            "api-version": "3.0",
            "from": "en",
            "to": [target_language],
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self._key,
            "Ocp-Apim-Subscription-Region": self._region,
            "Content-type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }

        body = [{"text": text} for text in texts]

        response = requests.post(url, params=params, headers=headers, json=body, timeout=10)
        response.raise_for_status()
        result = response.json()
        return [item["translations"][0]["text"] for item in result]
