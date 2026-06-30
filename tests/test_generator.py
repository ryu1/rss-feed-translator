from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import defusedxml.ElementTree as ET  # type: ignore[import-untyped]

from src.generator import generate_rss
from src.models import TranslatedArticle


def make_translated_article(
    n: int,
    natural_title: str | None = None,
    summary: str | None = None,
) -> TranslatedArticle:
    now = datetime.now(tz=timezone.utc)
    return TranslatedArticle(
        guid=f"https://example.com/{n}",
        original_title=f"Original Title {n}",
        original_description=f"Original desc {n}",
        translated_title=f"翻訳タイトル {n}",
        translated_description=f"翻訳説明 {n}",
        natural_title=natural_title,
        summary=summary,
        link=f"https://example.com/{n}",
        published=now,
        source="Test Feed",
        translated_at=now,
    )


def test_generate_rss_creates_valid_xml(tmp_path: Path) -> None:
    output = str(tmp_path / "rss.xml")
    articles = [make_translated_article(i) for i in range(3)]
    generate_rss(articles, output)

    tree = ET.parse(output)
    root = tree.getroot()
    assert root.tag == "rss"
    items = root.findall("./channel/item")
    assert len(items) == 3


def test_generate_rss_uses_natural_title_when_available(
    tmp_path: Path,
) -> None:
    output = str(tmp_path / "rss.xml")
    articles = [
        make_translated_article(
            1,
            natural_title="自然なタイトル",
            summary="要約文",
        )
    ]
    generate_rss(articles, output)

    tree = ET.parse(output)
    root = tree.getroot()
    title_el = root.find("./channel/item/title")
    assert title_el is not None
    assert title_el.text == "[翻訳] 自然なタイトル"


def test_generate_rss_falls_back_to_translated_title(tmp_path: Path) -> None:
    output = str(tmp_path / "rss.xml")
    articles = [make_translated_article(1, natural_title=None)]
    generate_rss(articles, output)

    tree = ET.parse(output)
    root = tree.getroot()
    title_el = root.find("./channel/item/title")
    assert title_el is not None
    assert title_el.text == "[翻訳] 翻訳タイトル 1"


def test_generate_rss_respects_max_items(tmp_path: Path) -> None:
    output = str(tmp_path / "rss.xml")
    articles = [make_translated_article(i) for i in range(10)]
    generate_rss(articles, output, max_items=3)

    tree = ET.parse(output)
    root = tree.getroot()
    items = root.findall("./channel/item")
    assert len(items) == 3


def test_generate_rss_preserves_guid(tmp_path: Path) -> None:
    output = str(tmp_path / "rss.xml")
    articles = [make_translated_article(42)]
    generate_rss(articles, output)

    tree = ET.parse(output)
    root = tree.getroot()
    guid_el = root.find("./channel/item/guid")
    assert guid_el is not None
    assert guid_el.text == "https://example.com/42"
