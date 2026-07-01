from __future__ import annotations

import logging
import unittest.mock
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.models import TranslatedArticle
from src.report_generator import generate_report


def _make_article(
    guid: str,
    source: str,
    published: datetime,
    *,
    translated_title: str | None = "翻訳タイトル",
    translated_description: str | None = "翻訳説明",
    summary: str | None = "要約1行目。\n要約2行目。\n要約3行目。",
) -> TranslatedArticle:
    return TranslatedArticle(
        guid=guid,
        original_title="Original Title",
        original_description="Original description text.",
        translated_title=translated_title,
        translated_description=translated_description,
        natural_title=None,
        summary=summary,
        link=f"https://example.com/{guid}",
        published=published,
        source=source,
        translated_at=datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc),
    )


def test_generate_report_creates_file(tmp_path: Path) -> None:
    output = str(tmp_path / "report.html")
    articles = [
        _make_article("1", "Feed A", datetime(2026, 7, 1, tzinfo=timezone.utc)),
    ]
    generate_report(articles, output)
    assert Path(output).exists()


def test_generate_report_empty_articles_does_not_create_file(tmp_path: Path) -> None:
    output = str(tmp_path / "report.html")
    generate_report([], output)
    assert not Path(output).exists()


def test_generate_report_contains_feed_section(tmp_path: Path) -> None:
    output = str(tmp_path / "report.html")
    articles = [
        _make_article("1", "Feed A", datetime(2026, 7, 1, tzinfo=timezone.utc)),
    ]
    generate_report(articles, output)
    html = Path(output).read_text(encoding="utf-8")
    assert "Feed A" in html


def test_generate_report_contains_original_title(tmp_path: Path) -> None:
    output = str(tmp_path / "report.html")
    articles = [
        _make_article("1", "Feed A", datetime(2026, 7, 1, tzinfo=timezone.utc)),
    ]
    generate_report(articles, output)
    html = Path(output).read_text(encoding="utf-8")
    assert "Original Title" in html


def test_generate_report_shows_translation_skipped_badge_when_no_translated_title(
    tmp_path: Path,
) -> None:
    output = str(tmp_path / "report.html")
    articles = [
        _make_article(
            "1",
            "Feed A",
            datetime(2026, 7, 1, tzinfo=timezone.utc),
            translated_title=None,
        ),
    ]
    generate_report(articles, output)
    html = Path(output).read_text(encoding="utf-8")
    assert "翻訳スキップ" in html


def test_generate_report_shows_no_summary_when_none(tmp_path: Path) -> None:
    output = str(tmp_path / "report.html")
    articles = [
        _make_article(
            "1",
            "Feed A",
            datetime(2026, 7, 1, tzinfo=timezone.utc),
            summary=None,
        ),
    ]
    generate_report(articles, output)
    html = Path(output).read_text(encoding="utf-8")
    assert "要約なし" in html


def test_generate_report_shows_no_translation_when_none(tmp_path: Path) -> None:
    output = str(tmp_path / "report.html")
    articles = [
        _make_article(
            "1",
            "Feed A",
            datetime(2026, 7, 1, tzinfo=timezone.utc),
            translated_description=None,
        ),
    ]
    generate_report(articles, output)
    html = Path(output).read_text(encoding="utf-8")
    assert "翻訳なし" in html


def test_generate_report_limits_items_per_feed(tmp_path: Path) -> None:
    output = str(tmp_path / "report.html")
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    articles = [
        _make_article(str(i), "Feed A", base.replace(hour=i % 24)) for i in range(15)
    ]
    generate_report(articles, output, items_per_feed=10)
    html = Path(output).read_text(encoding="utf-8")
    # 10件制限: 記事カードの数を確認するためにリンクのカウントを使う
    assert html.count("https://example.com/") == 10


def test_generate_report_escapes_html_in_content(tmp_path: Path) -> None:
    output = str(tmp_path / "report.html")
    articles = [
        TranslatedArticle(
            guid="1",
            original_title="<script>alert('xss')</script>",
            original_description="desc",
            translated_title="翻訳",
            translated_description="説明",
            natural_title=None,
            summary=None,
            link="https://example.com/1",
            published=datetime(2026, 7, 1, tzinfo=timezone.utc),
            source="Feed A",
            translated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )
    ]
    generate_report(articles, output)
    html = Path(output).read_text(encoding="utf-8")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_generate_report_multiple_feeds(tmp_path: Path) -> None:
    output = str(tmp_path / "report.html")
    articles = [
        _make_article("1", "Feed A", datetime(2026, 7, 1, tzinfo=timezone.utc)),
        _make_article("2", "Feed B", datetime(2026, 7, 1, tzinfo=timezone.utc)),
    ]
    generate_report(articles, output)
    html = Path(output).read_text(encoding="utf-8")
    assert "Feed A" in html
    assert "Feed B" in html


def test_generate_report_logs_warning_on_write_failure(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    output = str(tmp_path / "report.html")
    articles = [
        _make_article("1", "Feed A", datetime(2026, 7, 1, tzinfo=timezone.utc)),
    ]
    with unittest.mock.patch(
        "pathlib.Path.write_text", side_effect=OSError("disk full")
    ):
        with caplog.at_level(logging.WARNING, logger="src.report_generator"):
            generate_report(articles, output)
    assert any("Failed to write report" in r.message for r in caplog.records)
