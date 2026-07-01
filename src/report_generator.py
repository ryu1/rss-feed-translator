from __future__ import annotations

import html
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from src.models import TranslatedArticle

logger = logging.getLogger(__name__)


def generate_report(
    articles: list[TranslatedArticle],
    output_path: str,
    items_per_feed: int = 10,
) -> None:
    """翻訳・要約レビューレポートを HTML ファイルとして生成する。"""
    if not articles:
        return

    by_feed: dict[str, list[TranslatedArticle]] = defaultdict(list)
    for article in articles:
        by_feed[article.source].append(article)

    # フィードごとに published 降順で最新 items_per_feed 件に絞り込む
    feed_sections: dict[str, list[TranslatedArticle]] = {}
    for source, feed_articles in by_feed.items():
        sorted_articles = sorted(feed_articles, key=lambda a: a.published, reverse=True)
        feed_sections[source] = sorted_articles[:items_per_feed]

    total_shown = sum(len(v) for v in feed_sections.values())
    generated_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections_html = "\n".join(
        _render_feed_section(source, feed_articles)
        for source, feed_articles in feed_sections.items()
    )

    page = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>翻訳・要約レビューレポート</title>
<style>
  body {{
    font-family: sans-serif; max-width: 960px; margin: 0 auto;
    padding: 1rem; color: #333;
  }}
  h1 {{
    font-size: 1.4rem; border-bottom: 2px solid #333;
    padding-bottom: 0.4rem;
  }}
  h2 {{
    font-size: 1.2rem; margin-top: 2rem;
    border-left: 4px solid #666; padding-left: 0.6rem;
  }}
  .meta {{ color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }}
  .card {{
    border: 1px solid #ddd; border-radius: 4px;
    padding: 1rem; margin-bottom: 1rem;
  }}
  .card-title {{
    font-size: 1rem; font-weight: bold;
    margin-bottom: 0.4rem;
  }}
  .original-title {{ color: #555; font-size: 0.9rem; }}
  .badge {{
    display: inline-block; font-size: 0.75rem;
    padding: 0.1rem 0.4rem; border-radius: 3px;
    background: #f0c040; color: #333; margin-left: 0.5rem;
  }}
  .label {{
    font-size: 0.8rem; color: #888;
    margin-top: 0.6rem; margin-bottom: 0.2rem;
  }}
  .summary {{ white-space: pre-wrap; font-size: 0.9rem; }}
  .none-text {{ color: #aaa; font-style: italic; font-size: 0.9rem; }}
  details summary {{ cursor: pointer; font-size: 0.8rem; color: #555; }}
  details p {{
    font-size: 0.85rem; color: #555;
    margin: 0.4rem 0 0; white-space: pre-wrap;
  }}
  .card-footer {{ margin-top: 0.6rem; font-size: 0.8rem; }}
  .card-footer a {{ color: #0066cc; }}
  .no-articles {{ color: #aaa; font-style: italic; }}
</style>
</head>
<body>
<h1>翻訳・要約レビューレポート</h1>
<p class="meta">
  生成日時: {html.escape(generated_at)} &nbsp;|&nbsp;
  表示件数: {total_shown} 件
</p>
{sections_html}
</body>
</html>"""

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(page, encoding="utf-8")
        logger.info(
            "Report generated: %s (%d articles shown)",
            output_path,
            total_shown,
        )
    except OSError as e:
        logger.warning("Failed to write report to %s: %s", output_path, e)


def _render_feed_section(source: str, articles: list[TranslatedArticle]) -> str:
    h_source = html.escape(source)
    if not articles:
        return f'<h2>{h_source}</h2>\n<p class="no-articles">記事なし</p>'
    cards = "\n".join(_render_card(a) for a in articles)
    return f"<h2>{h_source}</h2>\n{cards}"


def _render_card(article: TranslatedArticle) -> str:
    original_title = html.escape(article.original_title)
    link = html.escape(article.link)

    # タイトル行
    if article.translated_title:
        title_html = (
            f'<div class="card-title">{html.escape(article.translated_title)}</div>'
            f'<div class="original-title">{original_title}</div>'
        )
    else:
        title_html = (
            f'<div class="card-title">{original_title}'
            f'<span class="badge">翻訳スキップ</span></div>'
        )

    # 原文説明（折りたたみ）
    original_desc = html.escape(article.original_description)
    original_html = (
        f"<details><summary>原文説明（英語）</summary><p>{original_desc}</p></details>"
    )

    # 翻訳済み説明
    if article.translated_description:
        trans_desc_html = html.escape(article.translated_description)
    else:
        trans_desc_html = '<span class="none-text">翻訳なし</span>'

    # 要約
    if article.summary:
        summary_html = f'<p class="summary">{html.escape(article.summary)}</p>'
    else:
        summary_html = '<p class="none-text">要約なし</p>'

    return f"""<div class="card">
  {title_html}
  <div class="label">原文説明</div>
  {original_html}
  <div class="label">翻訳済み説明</div>
  <p>{trans_desc_html}</p>
  <div class="label">要約</div>
  {summary_html}
  <div class="card-footer"><a href="{link}" target="_blank">元記事を開く</a></div>
</div>"""
