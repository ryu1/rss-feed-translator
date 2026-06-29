from __future__ import annotations

import pytest
import responses as resp_mock

from src.exceptions import FeedFetchError
from src.fetcher import fetch_all_feeds, fetch_feed
from src.models import FeedConfig

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>Article One</title>
      <description>Description one</description>
      <link>https://example.com/1</link>
      <guid>https://example.com/1</guid>
      <pubDate>Mon, 29 Jun 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Article Two</title>
      <description>Description two</description>
      <link>https://example.com/2</link>
      <guid>https://example.com/2</guid>
      <pubDate>Mon, 29 Jun 2026 11:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


@resp_mock.activate
def test_fetch_feed_returns_articles() -> None:
    resp_mock.add(resp_mock.GET, "https://example.com/rss", body=RSS_SAMPLE, status=200)
    feed = FeedConfig(name="Test", url="https://example.com/rss")
    articles = fetch_feed(feed, http_cache={})
    assert len(articles) == 2
    assert articles[0].title == "Article One"
    assert articles[0].source == "Test"
    assert articles[0].guid == "https://example.com/1"


@resp_mock.activate
def test_fetch_feed_raises_on_http_error() -> None:
    resp_mock.add(resp_mock.GET, "https://example.com/rss", status=500)
    feed = FeedConfig(name="Test", url="https://example.com/rss")
    with pytest.raises(FeedFetchError):
        fetch_feed(feed, http_cache={})


@resp_mock.activate
def test_fetch_feed_uses_etag() -> None:
    resp_mock.add(resp_mock.GET, "https://example.com/rss", status=304)
    feed = FeedConfig(name="Test", url="https://example.com/rss")
    http_cache = {"https://example.com/rss": {"etag": '"abc"', "last_modified": ""}}
    articles = fetch_feed(feed, http_cache=http_cache)
    assert articles == []


@resp_mock.activate
def test_fetch_all_feeds_continues_on_failure() -> None:
    resp_mock.add(resp_mock.GET, "https://example.com/good", body=RSS_SAMPLE, status=200)
    resp_mock.add(resp_mock.GET, "https://example.com/bad", status=500)
    feeds = [
        FeedConfig(name="Good", url="https://example.com/good"),
        FeedConfig(name="Bad", url="https://example.com/bad"),
    ]
    articles, _ = fetch_all_feeds(feeds, http_cache={})
    assert len(articles) == 2  # goodフィードの2件のみ取得
