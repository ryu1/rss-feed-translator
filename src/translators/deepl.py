from __future__ import annotations

import logging
import os
from typing import cast

from src.exceptions import TranslationError

logger = logging.getLogger(__name__)


class DeepLTranslator:
    def __init__(self) -> None:
        api_key = os.environ.get("DEEPL_API_KEY")
        if not api_key:
            raise EnvironmentError("DEEPL_API_KEY environment variable not set")
        try:
            import deepl

            self._translator = deepl.Translator(api_key)
        except Exception as e:
            raise TranslationError(f"Failed to initialize DeepL client: {e}") from e

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        if not texts:
            return []
        try:
            import deepl as _deepl

            raw = self._translator.translate_text(
                texts,
                target_lang=target_lang.upper(),
            )
            results = cast(list[_deepl.TextResult], raw)
            return [r.text for r in results]
        except Exception as e:
            msg = f"DeepL API error: {e}"
            raise TranslationError(msg) from e
