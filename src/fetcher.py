from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser  # type: ignore[import-untyped]
import requests

from src.exceptions import FeedFetchError
from src.models import Article, FeedConfig

logger = logging.getLogger(__name__)


def fetch_feed(
    feed: FeedConfig,
    http_cache: dict[str, dict[str, str]],
) -> list[Article]:
    headers: dict[str, str] = {}
    cached = http_cache.get(feed.url, {})
    if cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]
    if cached.get("last_modified"):
        headers["If-Modified-Since"] = cached["last_modified"]

    try:
        response = requests.get(feed.url, headers=headers, timeout=30)
    except requests.RequestException as e:
        raise FeedFetchError(f"Failed to fetch {feed.url}: {e}") from e

    if response.status_code == 304:
        logger.debug("Feed not modified (304): %s", feed.name)
        return []

    if not response.ok:
        raise FeedFetchError(f"HTTP {response.status_code} fetching {feed.url}")

    if response.headers.get("ETag"):
        http_cache.setdefault(feed.url, {})["etag"] = response.headers[
            "ETag"
        ]
    if response.headers.get("Last-Modified"):
        last_mod_header = response.headers["Last-Modified"]
        http_cache.setdefault(feed.url, {})["last_modified"] = last_mod_header

    parsed = feedparser.parse(response.text)
    articles: list[Article] = []
    for entry in parsed.entries:
        guid: str = str(
            getattr(entry, "id", None) or getattr(entry, "link", "")
        )
        title: str = getattr(entry, "title", "")
        description: str = (
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
        )
        link: str = getattr(entry, "link", "")
        published_parsed = getattr(entry, "published_parsed", None)
        if published_parsed:
            published = datetime(*published_parsed[:6]).replace(tzinfo=timezone.utc)
        else:
            published = datetime.now(tz=timezone.utc)

        if not guid or not title:
            continue
        articles.append(
            Article(
                guid=guid,
                title=title,
                description=description,
                link=link,
                published=published,
                source=feed.name,
            )
        )

    logger.info("Feed: %s — %d articles fetched", feed.name, len(articles))
    return articles


def fetch_all_feeds(
    feeds: list[FeedConfig],
    http_cache: dict[str, dict[str, str]],
) -> tuple[list[Article], dict[str, dict[str, str]]]:
    all_articles: list[Article] = []
    error_count = 0
    for feed in feeds:
        try:
            articles = fetch_feed(feed, http_cache)
            all_articles.extend(articles)
        except FeedFetchError as e:
            logger.warning("Feed fetch failed (skipped): %s — %s", feed.name, e)
            error_count += 1
    if error_count:
        logger.warning("Total feed fetch errors: %d", error_count)
    return all_articles, http_cache
