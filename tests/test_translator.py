from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.exceptions import TranslationError, TranslationSkippedError
from src.models import Article
from src.translator import get_translator, translate_articles, with_retry


class MockTranslator:
    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        return [f"翻訳: {t}" for t in texts]


class FailingTranslator:
    def __init__(self, fail_times: int = 3) -> None:
        self.calls = 0
        self.fail_times = fail_times

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise TranslationError("API error")
        return [f"翻訳: {t}" for t in texts]


def make_article(n: int) -> Article:
    return Article(
        guid=f"https://example.com/{n}",
        title=f"Title {n}",
        description=f"Description {n}",
        link=f"https://example.com/{n}",
        published=datetime.now(tz=timezone.utc),
        source="Test",
    )


def test_mock_translator_returns_translated_texts() -> None:
    translator = MockTranslator()
    result = translator.translate(["Hello", "World"])
    assert result == ["翻訳: Hello", "翻訳: World"]


def test_with_retry_succeeds_on_second_attempt() -> None:
    calls = 0

    def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise TranslationError("fail")
        return "ok"

    result = with_retry(flaky, max_attempts=3)
    assert result == "ok"
    assert calls == 2


def test_with_retry_raises_after_max_attempts() -> None:
    def always_fail() -> str:
        raise TranslationError("fail")

    with pytest.raises(TranslationSkippedError):
        with_retry(always_fail, max_attempts=3)


def test_translate_articles_batches_correctly() -> None:
    translator = MockTranslator()
    articles = [make_article(1), make_article(2)]
    results = translate_articles(articles, translator)
    assert len(results) == 2
    assert results[0] == ("翻訳: Title 1", "翻訳: Description 1")
    assert results[1] == ("翻訳: Title 2", "翻訳: Description 2")


def test_get_translator_raises_on_unknown_engine() -> None:
    with pytest.raises(ValueError, match="Unknown translator engine"):
        get_translator("unknown")
