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
from src.daily_budget import DailyBudget
from src.exceptions import TranslationSkippedError
from src.fetcher import fetch_all_feeds
from src.generator import generate_rss
from src.models import Article, FeedConfig, TranslatedArticle
from src.summarizer import get_summarizer, summarize_with_retry
from src.translator import _MAX_DESCRIPTION_CHARS, get_translator, translate_articles

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
            link_url=f.get("link_url", ""),
        )
        for f in feeds_config
    ]

    translator_config: dict[str, str] = config.get("translator", {})  # type: ignore[assignment]
    translator_engine = translator_config.get("engine", "google")
    translator_provider = translator_config.get("provider", "anthropic")
    daily_char_limit: int | None = (
        int(str(translator_config["daily_char_limit"]))
        if "daily_char_limit" in translator_config
        else None
    )

    summarizer_config: dict[str, object] = config.get("summarizer", {})  # type: ignore[assignment]
    summarizer_enabled = bool(summarizer_config.get("enabled", False))
    summarizer_engine = str(summarizer_config.get("engine", "openai"))
    summarizer_model = str(summarizer_config.get("model", "gpt-4o-mini"))
    summarizer_prompt = str(summarizer_config.get("prompt", ""))
    summarizer_provider = str(summarizer_config.get("provider", "anthropic"))

    output_config: dict[str, object] = config.get("output", {})  # type: ignore[assignment]
    max_items = int(str(output_config.get("max_items", 200)))

    cache_config: dict[str, str] = config.get("cache", {})  # type: ignore[assignment]
    cache_path = cache_config.get("path", "cache/translated.json")
    http_cache_path = cache_config.get("http_cache_path", "cache/http_cache.json")
    char_usage_path = cache_config.get("char_usage_path", "cache/char_usage.json")

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
    budget_skipped: list[Article] = []

    if new_articles:
        try:
            translator = get_translator(translator_engine, provider=translator_provider)
        except Exception as e:
            logger.error("Failed to initialize translator: %s", e)
            translator = None

        if translator is not None:
            # バジェット対象記事（実際に翻訳する）
            articles_to_translate: list[Article] = []

            if daily_char_limit is not None:
                budget = DailyBudget(path=char_usage_path, limit=daily_char_limit)
                for article in new_articles:
                    char_count = len(article.title) + len(
                        article.description[:_MAX_DESCRIPTION_CHARS]
                    )
                    if budget.can_translate(char_count):
                        articles_to_translate.append(article)
                    else:
                        budget_skipped.append(article)
                if budget_skipped:
                    logger.warning(
                        "Daily character budget exceeded (%d/%d used):"
                        " skipping %d articles",
                        budget.limit - budget.remaining(),
                        budget.limit,
                        len(budget_skipped),
                    )
            else:
                articles_to_translate = new_articles

            logger.info(
                "Translating %d articles (engine=%s)...",
                len(articles_to_translate),
                translator_engine,
            )
            if articles_to_translate:
                try:
                    results = translate_articles(articles_to_translate, translator)
                except TranslationSkippedError as e:
                    logger.error(
                        "Batch translation failed, skipping cache write: %s", e
                    )
                    error_count += len(articles_to_translate)
                    results = None
                except Exception as e:
                    logger.error(
                        "Unexpected translation error, skipping cache write: %s", e
                    )
                    error_count += len(articles_to_translate)
                    results = None

                if results is not None:
                    now = datetime.now(tz=timezone.utc)
                    total_chars = sum(
                        len(a.title) + len(a.description[:_MAX_DESCRIPTION_CHARS])
                        for a in articles_to_translate
                    )
                    if daily_char_limit is not None:
                        budget.consume(total_chars)
                    for article, (translated_title, translated_description) in zip(
                        articles_to_translate, results
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
                "Translated: %d articles (%d skipped, %d budget-skipped)",
                translated_count,
                skipped_count,
                len(budget_skipped),
            )

    summarized_count = 0
    if summarizer_enabled and new_articles:
        try:
            summarizer = get_summarizer(
                summarizer_engine,
                summarizer_model,
                summarizer_prompt,
                provider=summarizer_provider,
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

    # バジェット超過でスキップした記事はキャッシュには保存せず RSS 生成のみに含める
    now = datetime.now(tz=timezone.utc)
    budget_skipped_articles = [
        TranslatedArticle(
            guid=a.guid,
            original_title=a.title,
            original_description=a.description,
            translated_title=None,
            translated_description=None,
            natural_title=None,
            summary=None,
            link=a.link,
            published=a.published,
            source=a.source,
            translated_at=now,
        )
        for a in budget_skipped
    ]
    all_translated = list(translated_cache.values()) + budget_skipped_articles

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
                link=feed.link_url,
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
