from __future__ import annotations

import logging
import os

from src.exceptions import TranslationError

logger = logging.getLogger(__name__)


class OpenAITranslator:
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set")
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)
        except Exception as e:
            msg = f"Failed to initialize OpenAI client: {e}"
            raise TranslationError(msg) from e

    _SEP = "<<<TRANSLATION_SEP>>>"
    _CHUNK_SIZE = 20

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        if not texts:
            return []
        results: list[str] = []
        for i in range(0, len(texts), self._CHUNK_SIZE):
            chunk = texts[i : i + self._CHUNK_SIZE]
            results.extend(self._translate_chunk(chunk, target_lang))
        return results

    def _translate_chunk(self, texts: list[str], target_lang: str) -> list[str]:
        joined = f"\n{self._SEP}\n".join(texts)
        sep = self._SEP
        prompt = (
            f"Translate each section separated by '{sep}' into {target_lang}. "
            f"Return only the translations separated by '\\n{sep}\\n', "
            "in the same order. "
            "Do not add any explanation.\n\n" + joined
        )
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content or ""
            parts = [t.strip() for t in content.split(f"\n{self._SEP}\n")]
            if len(parts) != len(texts):
                msg = f"Expected {len(texts)} translations, got {len(parts)}"
                raise TranslationError(msg)
            return parts
        except Exception as e:
            msg = f"OpenAI translation error: {e}"
            raise TranslationError(msg) from e
