from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import responses as resp_mock

from src.models import FeedConfig, TranslatedArticle

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>New Article</title>
      <description>New description</description>
      <link>https://example.com/new</link>
      <guid>https://example.com/new</guid>
      <pubDate>Mon, 29 Jun 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


@resp_mock.activate
def test_pipeline_skips_cached_articles(tmp_path: Path) -> None:
    """キャッシュ済みGUIDの記事は翻訳をスキップする"""
    from src.cache import load_translated_cache, save_translated_cache
    from src.fetcher import fetch_all_feeds

    cache_path = str(tmp_path / "translated.json")
    now = datetime.now(tz=timezone.utc)
    existing = TranslatedArticle(
        guid="https://example.com/new",
        original_title="New Article",
        original_description="New description",
        translated_title="新しい記事",
        translated_description="新しい説明",
        natural_title=None,
        summary=None,
        link="https://example.com/new",
        published=now,
        source="Test Feed",
        translated_at=now,
    )
    save_translated_cache(cache_path, {existing.guid: existing})

    resp_mock.add(resp_mock.GET, "https://example.com/rss", body=RSS_SAMPLE, status=200)
    feeds = [FeedConfig(name="Test Feed", url="https://example.com/rss")]
    articles, _ = fetch_all_feeds(feeds, http_cache={})

    cache = load_translated_cache(cache_path)
    new_articles = [a for a in articles if a.guid not in cache]
    assert len(new_articles) == 0  # 既にキャッシュ済み
