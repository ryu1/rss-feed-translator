from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.models import TranslatedArticle

logger = logging.getLogger(__name__)


def _parse_dt(value: str) -> datetime:
    """Parse an ISO-format datetime string, attaching UTC if tzinfo is absent."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_translated_cache(path: str) -> dict[str, TranslatedArticle]:
    if not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data: dict[str, dict[str, object]] = json.load(f)
    result: dict[str, TranslatedArticle] = {}
    for guid, item in data.items():
        translated_title: str | None = (
            str(item["translated_title"]) if item.get("translated_title") else None
        )
        translated_description: str | None = (
            str(item["translated_description"])
            if item.get("translated_description")
            else None
        )
        natural_title: str | None = (
            str(item["natural_title"]) if item.get("natural_title") else None
        )
        summary: str | None = str(item["summary"]) if item.get("summary") else None
        result[guid] = TranslatedArticle(
            guid=guid,
            original_title=str(item["original_title"]),
            original_description=str(item["original_description"]),
            translated_title=translated_title,
            translated_description=translated_description,
            natural_title=natural_title,
            summary=summary,
            link=str(item["link"]),
            published=_parse_dt(str(item["published"])),
            source=str(item["source"]),
            translated_at=_parse_dt(str(item["translated_at"])),
        )
    logger.debug("Loaded %d entries from cache: %s", len(result), path)
    return result


def save_translated_cache(path: str, cache: dict[str, TranslatedArticle]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, dict[str, object]] = {}
    for guid, article in cache.items():
        data[guid] = {
            "original_title": article.original_title,
            "original_description": article.original_description,
            "translated_title": article.translated_title,
            "translated_description": article.translated_description,
            "natural_title": article.natural_title,
            "summary": article.summary,
            "link": article.link,
            "published": article.published.isoformat(),
            "source": article.source,
            "translated_at": article.translated_at.isoformat(),
        }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.debug("Saved %d entries to cache: %s", len(cache), path)


def load_http_cache(path: str) -> dict[str, dict[str, str]]:
    if not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def save_http_cache(path: str, cache: dict[str, dict[str, str]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
