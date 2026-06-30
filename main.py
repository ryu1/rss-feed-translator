from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone

import yaml

from src.cache import (
    load_http_cache,
    load_translated_cache,
    save_http_cache,
    save_translated_cache,
)
from src.exceptions import TranslationSkippedError
from src.fetcher import fetch_all_feeds
from src.generator import generate_rss
from src.models import Article, FeedConfig, TranslatedArticle
from src.summarizer import get_summarizer, summarize_with_retry
from src.translator import get_translator, translate_articles

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict[object, object]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def main() -> None:
    start = time.time()
    logger.info("Starting RSS feed translator")

    try:
        config = load_config()
    except Exception as e:
        logger.error("Failed to load config: %s", e)
        return

    feeds_config: list[dict[str, str]] = config.get("feeds", [])  # type: ignore[assignment]
    feeds = [
        FeedConfig(
            name=f["name"],
            url=f["url"],
            output_path=f.get("output_path"),
        )
        for f in feeds_config
    ]

    translator_config: dict[str, str] = config.get("translator", {})  # type: ignore[assignment]
    translator_engine = translator_config.get("engine", "google")

    summarizer_config: dict[str, object] = config.get("summarizer", {})  # type: ignore[assignment]
    summarizer_enabled = bool(summarizer_config.get("enabled", False))
    summarizer_engine = str(summarizer_config.get("engine", "openai"))
    summarizer_model = str(summarizer_config.get("model", "gpt-4o-mini"))
    summarizer_prompt = str(summarizer_config.get("prompt", ""))

    output_config: dict[str, object] = config.get("output", {})  # type: ignore[assignment]
    max_items = int(str(output_config.get("max_items", 200)))

    cache_config: dict[str, str] = config.get("cache", {})  # type: ignore[assignment]
    cache_path = cache_config.get("path", "cache/translated.json")
    http_cache_path = cache_config.get("http_cache_path", "cache/http_cache.json")

    translated_cache = load_translated_cache(cache_path)
    http_cache = load_http_cache(http_cache_path)

    logger.info("Fetching %d feeds...", len(feeds))
    try:
        all_articles, http_cache = fetch_all_feeds(feeds, http_cache)
    except Exception as e:
        logger.error("Unexpected error during feed fetch: %s", e)
        all_articles = []

    new_articles = [a for a in all_articles if a.guid not in translated_cache]
    logger.info(
        "Fetched %d total articles, %d new", len(all_articles), len(new_articles)
    )

    translated_count = 0
    skipped_count = 0
    error_count = 0

    if new_articles:
        try:
            translator = get_translator(translator_engine)
        except Exception as e:
            logger.error("Failed to initialize translator: %s", e)
            translator = None

        if translator is not None:
            logger.info(
                "Translating %d articles (engine=%s)...",
                len(new_articles),
                translator_engine,
            )
            try:
                results = translate_articles(new_articles, translator)
            except TranslationSkippedError as e:
                logger.error("Batch translation failed: %s", e)
                results = [("", "")] * len(new_articles)
                error_count += len(new_articles)
            except Exception as e:
                logger.error("Unexpected translation error: %s", e)
                results = [("", "")] * len(new_articles)
                error_count += len(new_articles)

            now = datetime.now(tz=timezone.utc)
            for article, (translated_title, translated_description) in zip(
                new_articles, results
            ):
                if not translated_title:
                    skipped_count += 1
                    translated_cache[article.guid] = TranslatedArticle(
                        guid=article.guid,
                        original_title=article.title,
                        original_description=article.description,
                        translated_title=None,
                        translated_description=None,
                        natural_title=None,
                        summary=None,
                        link=article.link,
                        published=article.published,
                        source=article.source,
                        translated_at=now,
                    )
                    continue
                translated_cache[article.guid] = TranslatedArticle(
                    guid=article.guid,
                    original_title=article.title,
                    original_description=article.description,
                    translated_title=translated_title,
                    translated_description=translated_description,
                    natural_title=None,
                    summary=None,
                    link=article.link,
                    published=article.published,
                    source=article.source,
                    translated_at=now,
                )
                translated_count += 1

            logger.info(
                "Translated: %d articles (%d skipped)", translated_count, skipped_count
            )

    summarized_count = 0
    if summarizer_enabled and new_articles:
        try:
            summarizer = get_summarizer(
                summarizer_engine, summarizer_model, summarizer_prompt
            )
        except Exception as e:
            logger.error("Failed to initialize summarizer: %s", e)
            summarizer = None

        if summarizer is not None:
            to_summarize = [
                translated_cache[a.guid]
                for a in new_articles
                if a.guid in translated_cache
                and translated_cache[a.guid].translated_title
            ]
            logger.info(
                "Summarizing %d articles with LLM (summarizer=%s/%s)...",
                len(to_summarize),
                summarizer_engine,
                summarizer_model,
            )
            for cached_article in to_summarize:
                source_article = Article(
                    guid=cached_article.guid,
                    title=cached_article.original_title,
                    description=cached_article.original_description,
                    link=cached_article.link,
                    published=cached_article.published,
                    source=cached_article.source,
                )
                try:
                    natural_title, summary = summarize_with_retry(
                        summarizer, source_article
                    )
                except Exception as e:
                    logger.error(
                        "Unexpected summarization error for %s: %s",
                        cached_article.guid,
                        e,
                    )
                    error_count += 1
                    continue
                if natural_title:
                    cached_article.natural_title = natural_title
                    cached_article.summary = summary
                    summarized_count += 1
                else:
                    error_count += 1
            logger.info("Summarized: %d articles", summarized_count)

    try:
        save_translated_cache(cache_path, translated_cache)
        save_http_cache(http_cache_path, http_cache)
    except Exception as e:
        logger.error("Failed to save cache: %s", e)

    all_translated = list(translated_cache.values())

    for feed in feeds:
        if feed.output_path is None:
            continue
        feed_articles = [a for a in all_translated if a.source == feed.name]
        try:
            generate_rss(
                feed_articles,
                feed.output_path,
                max_items=max_items,
                title=feed.name,
                description=f"{feed.name} 日本語翻訳フィード",
            )
        except Exception as e:
            logger.error("Failed to generate RSS for %s: %s", feed.name, e)

    elapsed = time.time() - start
    logger.info(
        "Done in %.1fs | fetched=%d new=%d translated=%d summarized=%d errors=%d",
        elapsed,
        len(all_articles),
        len(new_articles),
        translated_count,
        summarized_count,
        error_count,
    )


if __name__ == "__main__":
    main()
