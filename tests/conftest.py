from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models import Article, FeedConfig, TranslatedArticle


@pytest.fixture
def sample_feed_config() -> FeedConfig:
    return FeedConfig(name="Test Feed", url="https://example.com/rss")


@pytest.fixture
def sample_article() -> Article:
    return Article(
        guid="https://example.com/1",
        title="Test Article",
        description="Test description",
        link="https://example.com/1",
        published=datetime(2026, 6, 29, 10, 0, 0, tzinfo=timezone.utc),
        source="Test Feed",
    )


@pytest.fixture
def sample_translated_article() -> TranslatedArticle:
    now = datetime(2026, 6, 29, 10, 5, 0, tzinfo=timezone.utc)
    return TranslatedArticle(
        guid="https://example.com/1",
        original_title="Test Article",
        original_description="Test description",
        translated_title="テスト記事",
        translated_description="テスト説明",
        natural_title="自然なテスト記事タイトル",
        summary="要約1行目。\n要約2行目。\n要約3行目。",
        link="https://example.com/1",
        published=datetime(2026, 6, 29, 10, 0, 0, tzinfo=timezone.utc),
        source="Test Feed",
        translated_at=now,
    )
