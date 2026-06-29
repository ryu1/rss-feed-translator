from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.exceptions import SummarizationError
from src.models import Article
from src.summarizer import get_summarizer, summarize_with_retry


class MockSummarizer:
    def summarize(self, article: Article) -> tuple[str, str]:
        return (f"自然: {article.title}", f"要約: {article.description}")


class FailingSummarizer:
    def summarize(self, article: Article) -> tuple[str, str]:
        raise SummarizationError("API error")


def make_article() -> Article:
    return Article(
        guid="https://example.com/1",
        title="AI Breakthrough",
        description="Researchers found a new approach.",
        link="https://example.com/1",
        published=datetime.now(tz=timezone.utc),
        source="Ars Technica",
    )


def test_mock_summarizer_returns_tuple() -> None:
    article = make_article()
    result = MockSummarizer().summarize(article)
    assert result == ("自然: AI Breakthrough", "要約: Researchers found a new approach.")


def test_summarize_with_retry_returns_none_on_failure() -> None:
    article = make_article()
    with patch("time.sleep"):
        result = summarize_with_retry(FailingSummarizer(), article, max_attempts=3)
    assert result == (None, None)


def test_summarize_with_retry_succeeds() -> None:
    article = make_article()
    result = summarize_with_retry(MockSummarizer(), article, max_attempts=3)
    assert result[0] is not None
    assert result[1] is not None


def test_get_summarizer_raises_on_unknown_engine() -> None:
    with pytest.raises(ValueError, match="Unknown summarizer engine"):
        get_summarizer("unknown", "model", "prompt")
