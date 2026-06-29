from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeedConfig:
    name: str
    url: str


@dataclass(frozen=True)
class Article:
    guid: str
    title: str
    description: str
    link: str
    published: datetime
    source: str


@dataclass
class TranslatedArticle:
    guid: str
    original_title: str
    original_description: str
    translated_title: str | None
    translated_description: str | None
    natural_title: str | None
    summary: str | None
    link: str
    published: datetime
    source: str
    translated_at: datetime
