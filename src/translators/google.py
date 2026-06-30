from __future__ import annotations

import logging
import os

import requests

from src.exceptions import TranslationError

logger = logging.getLogger(__name__)

_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"


class GoogleTranslator:
    def __init__(self) -> None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY environment variable not set")
        self._api_key = api_key

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        if not texts:
            return []
        try:
            response = requests.post(
                _TRANSLATE_URL,
                params={"key": self._api_key},
                json={"q": texts, "target": target_lang, "format": "text"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return [item["translatedText"] for item in data["data"]["translations"]]
        except Exception as e:
            msg = f"Google Translate API error: {e}"
            raise TranslationError(msg) from e
