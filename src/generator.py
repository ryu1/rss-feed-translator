from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import format_datetime
from pathlib import Path

from src.models import TranslatedArticle

logger = logging.getLogger(__name__)


def generate_rss(
    articles: list[TranslatedArticle],
    output_path: str,
    max_items: int = 200,
) -> None:
    sorted_articles = sorted(
        articles,
        key=lambda a: a.published,
        reverse=True,
    )[:max_items]

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "RSS Feed Translator"
    ET.SubElement(channel, "description").text = "海外ITニュースの日本語翻訳フィード"
    ET.SubElement(channel, "link").text = "https://github.com"

    for article in sorted_articles:
        item = ET.SubElement(channel, "item")

        display_title = (
            article.natural_title
            or article.translated_title
            or article.original_title
        )
        ET.SubElement(item, "title").text = display_title

        display_description = (
            article.summary
            or article.translated_description
            or article.original_description
        )
        ET.SubElement(item, "description").text = display_description

        ET.SubElement(item, "link").text = article.link

        pub_date = article.published
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        ET.SubElement(item, "pubDate").text = format_datetime(pub_date)

        ET.SubElement(item, "source").text = article.source
        ET.SubElement(
            item,
            "guid",
            isPermaLink="false",
        ).text = article.guid

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    logger.info(
        "RSS generated: %s (%d articles total)",
        output_path,
        len(sorted_articles),
    )
