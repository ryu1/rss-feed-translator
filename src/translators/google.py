from __future__ import annotations

import logging
import os

from src.exceptions import TranslationError

logger = logging.getLogger(__name__)


class GoogleTranslator:
    def __init__(self) -> None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY environment variable not set")
        try:
            from google.cloud import (  # type: ignore[import-untyped]
                translate_v2 as google_translate,
            )

            self._client = google_translate.Client(client_options={"api_key": api_key})
        except Exception as e:
            msg = f"Failed to initialize Google Translate client: {e}"
            raise TranslationError(msg) from e

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        if not texts:
            return []
        try:
            results = self._client.translate(texts, target_language=target_lang)
            return [r["translatedText"] for r in results]
        except Exception as e:
            msg = f"Google Translate API error: {e}"
            raise TranslationError(msg) from e
