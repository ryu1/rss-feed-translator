from __future__ import annotations

import logging
import time
from typing import Callable, Protocol, TypeVar

from src.exceptions import TranslationError, TranslationSkippedError
from src.models import Article

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Translator(Protocol):
    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]: ...


def with_retry(fn: Callable[[], T], max_attempts: int = 3) -> T:
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except TranslationError as e:
            if attempt == max_attempts:
                logger.error("Translation failed after %d attempts: %s", max_attempts, e)
                raise TranslationSkippedError(str(e)) from e
            wait = 2 ** (attempt - 1)
            logger.warning(
                "Translation attempt %d/%d failed, retrying in %ds: %s",
                attempt,
                max_attempts,
                wait,
                e,
            )
            time.sleep(wait)
    raise TranslationSkippedError("Unreachable")


def translate_articles(
    articles: list[Article], translator: Translator
) -> list[tuple[str, str]]:
    titles = [a.title for a in articles]
    descriptions = [a.description for a in articles]
    all_texts = titles + descriptions

    def _translate() -> list[str]:
        return translator.translate(all_texts)

    translated = with_retry(_translate)
    mid = len(articles)
    return list(zip(translated[:mid], translated[mid:]))


def get_translator(engine: str) -> Translator:
    if engine == "google":
        from src.translators.google import GoogleTranslator

        return GoogleTranslator()
    if engine == "openai":
        from src.translators.openai import OpenAITranslator

        return OpenAITranslator()
    if engine == "deepl":
        from src.translators.deepl import DeepLTranslator

        return DeepLTranslator()
    raise ValueError(f"Unknown translator engine: {engine!r}. Choose from: google, openai, deepl")
