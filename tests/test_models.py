from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models import Article, FeedConfig, TranslatedArticle


def test_feed_config_is_frozen() -> None:
    config = FeedConfig(name="Test", url="https://example.com/rss")
    with pytest.raises(Exception):
        config.name = "Changed"  # type: ignore[misc]


def test_article_fields() -> None:
    now = datetime.now(tz=timezone.utc)
    article = Article(
        guid="https://example.com/1",
        title="Test Title",
        description="Test description",
        link="https://example.com/1",
        published=now,
        source="Test Feed",
    )
    assert article.guid == "https://example.com/1"
    assert article.source == "Test Feed"


def test_translated_article_optional_fields() -> None:
    now = datetime.now(tz=timezone.utc)
    article = TranslatedArticle(
        guid="https://example.com/1",
        original_title="Original",
        original_description="Desc",
        translated_title=None,
        translated_description=None,
        natural_title=None,
        summary=None,
        link="https://example.com/1",
        published=now,
        source="Test",
        translated_at=now,
    )
    assert article.translated_title is None
    assert article.natural_title is None
