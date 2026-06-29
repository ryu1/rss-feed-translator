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
            raise TranslationError(f"Failed to initialize OpenAI client: {e}") from e

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        if not texts:
            return []
        joined = "\n---\n".join(texts)
        prompt = (
            f"Translate each section separated by '---' into {target_lang}. "
            "Return only the translations separated by '\\n---\\n', in the same order. "
            "Do not add any explanation.\n\n" + joined
        )
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content or ""
            parts = [t.strip() for t in content.split("\n---\n")]
            if len(parts) != len(texts):
                raise TranslationError(
                    f"Expected {len(texts)} translations, got {len(parts)}"
                )
            return parts
        except Exception as e:
            raise TranslationError(f"OpenAI translation error: {e}") from e
