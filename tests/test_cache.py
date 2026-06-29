from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.cache import load_translated_cache, save_translated_cache, load_http_cache, save_http_cache
from src.models import TranslatedArticle


@pytest.fixture
def tmp_cache_path(tmp_path: Path) -> str:
    return str(tmp_path / "translated.json")


@pytest.fixture
def sample_article() -> TranslatedArticle:
    now = datetime.now(tz=timezone.utc)
    return TranslatedArticle(
        guid="https://example.com/1",
        original_title="Original",
        original_description="Desc",
        translated_title="翻訳タイトル",
        translated_description="翻訳説明",
        natural_title="自然なタイトル",
        summary="要約1行目。\n要約2行目。\n要約3行目。",
        link="https://example.com/1",
        published=now,
        source="Test",
        translated_at=now,
    )


def test_save_and_load_translated_cache(tmp_cache_path: str, sample_article: TranslatedArticle) -> None:
    cache = {sample_article.guid: sample_article}
    save_translated_cache(tmp_cache_path, cache)

    loaded = load_translated_cache(tmp_cache_path)
    assert sample_article.guid in loaded
    assert loaded[sample_article.guid].translated_title == "翻訳タイトル"
    assert loaded[sample_article.guid].natural_title == "自然なタイトル"


def test_load_translated_cache_returns_empty_when_not_exists(tmp_cache_path: str) -> None:
    result = load_translated_cache(tmp_cache_path)
    assert result == {}


def test_translated_cache_handles_null_fields(tmp_cache_path: str) -> None:
    now = datetime.now(tz=timezone.utc)
    article = TranslatedArticle(
        guid="https://example.com/2",
        original_title="Title",
        original_description="Desc",
        translated_title=None,
        translated_description=None,
        natural_title=None,
        summary=None,
        link="https://example.com/2",
        published=now,
        source="Test",
        translated_at=now,
    )
    cache = {article.guid: article}
    save_translated_cache(tmp_cache_path, cache)
    loaded = load_translated_cache(tmp_cache_path)
    assert loaded[article.guid].translated_title is None
    assert loaded[article.guid].natural_title is None


def test_save_and_load_http_cache(tmp_path: Path) -> None:
    path = str(tmp_path / "http_cache.json")
    http_cache = {
        "https://example.com/rss": {
            "etag": '"abc123"',
            "last_modified": "Mon, 29 Jun 2026 10:00:00 GMT",
        }
    }
    save_http_cache(path, http_cache)
    loaded = load_http_cache(path)
    assert loaded["https://example.com/rss"]["etag"] == '"abc123"'
