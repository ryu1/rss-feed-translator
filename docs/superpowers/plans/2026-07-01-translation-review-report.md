# Translation Review Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 翻訳・要約の精度と必要性を確認できる HTML レビューレポートを GitHub Pages に公開する。

**Architecture:** `src/report_generator.py` に `generate_report()` 関数を追加する。`main.py` のパイプライン最後（キャッシュ保存後・RSS 生成後）に呼び出し、`all_translated` の全記事からフィードごとに最新10件を抽出して `docs/report.html` を生成する。失敗時は WARNING ログを出してパイプラインを継続する。

**Tech Stack:** Python 3.12+、標準ライブラリのみ（`html` モジュールによるエスケープ、`pathlib.Path` によるファイル書き込み）

## Global Constraints

- Python 3.12+（`str | None` 型構文必須）
- 外部 CSS フレームワーク・CDN・JavaScript 不使用
- 全関数にパラメータと戻り値の型ヒントを付与（`from __future__ import annotations`）
- `mypy --strict` で型エラーなし
- `ruff check` + `ruff format` でリントエラーなし（行長 88 文字）
- テストは `tests/test_report_generator.py` に配置、`pytest` で実行
- コミットメッセージは Conventional Commits 形式
- レポート出力先: `docs/report.html`
- フィードごとの表示件数: `items_per_feed`（デフォルト 10）
- `generate_report()` のシグネチャ:
  ```python
  def generate_report(
      articles: list[TranslatedArticle],
      output_path: str,
      items_per_feed: int = 10,
  ) -> None:
  ```
- `articles` が空リストの場合はファイルを更新せず即 return する
- ファイル書き込み失敗時は `logger.warning(...)` を出力してパイプラインを継続する（例外を再 raise しない）
- `config.yaml` に `report.output_path` と `report.items_per_feed` を追加する
- `main.py` では `config.get("report", {})` からこれらの設定を読み込む
- `update-rss.yml` のコミット対象パターンに `docs/report.html` を追加する

---

### Task 1: `src/report_generator.py` を実装する

**Files:**
- Create: `src/report_generator.py`
- Create: `tests/test_report_generator.py`

**Interfaces:**
- Consumes: `src/models.TranslatedArticle`（既存）
- Produces:
  ```python
  def generate_report(
      articles: list[TranslatedArticle],
      output_path: str,
      items_per_feed: int = 10,
  ) -> None:
  ```

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_report_generator.py` を以下の内容で作成する:

```python
from __future__ import annotations

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
        _make_article(str(i), "Feed A", base.replace(hour=i % 24))
        for i in range(15)
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_report_generator.py -v
```

期待結果: `ImportError: cannot import name 'generate_report' from 'src.report_generator'`

- [ ] **Step 3: `src/report_generator.py` を実装する**

```python
from __future__ import annotations

import html
import logging
from collections import defaultdict
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
    from datetime import datetime, timezone
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
  body {{ font-family: sans-serif; max-width: 960px; margin: 0 auto; padding: 1rem; color: #333; }}
  h1 {{ font-size: 1.4rem; border-bottom: 2px solid #333; padding-bottom: 0.4rem; }}
  h2 {{ font-size: 1.2rem; margin-top: 2rem; border-left: 4px solid #666; padding-left: 0.6rem; }}
  .meta {{ color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }}
  .card {{ border: 1px solid #ddd; border-radius: 4px; padding: 1rem; margin-bottom: 1rem; }}
  .card-title {{ font-size: 1rem; font-weight: bold; margin-bottom: 0.4rem; }}
  .original-title {{ color: #555; font-size: 0.9rem; }}
  .badge {{ display: inline-block; font-size: 0.75rem; padding: 0.1rem 0.4rem;
            border-radius: 3px; background: #f0c040; color: #333; margin-left: 0.5rem; }}
  .label {{ font-size: 0.8rem; color: #888; margin-top: 0.6rem; margin-bottom: 0.2rem; }}
  .summary {{ white-space: pre-wrap; font-size: 0.9rem; }}
  .none-text {{ color: #aaa; font-style: italic; font-size: 0.9rem; }}
  details summary {{ cursor: pointer; font-size: 0.8rem; color: #555; }}
  details p {{ font-size: 0.85rem; color: #555; margin: 0.4rem 0 0; white-space: pre-wrap; }}
  .card-footer {{ margin-top: 0.6rem; font-size: 0.8rem; }}
  .card-footer a {{ color: #0066cc; }}
  .no-articles {{ color: #aaa; font-style: italic; }}
</style>
</head>
<body>
<h1>翻訳・要約レビューレポート</h1>
<p class="meta">生成日時: {html.escape(generated_at)} &nbsp;|&nbsp; 表示件数: {total_shown} 件</p>
{sections_html}
</body>
</html>"""

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(page, encoding="utf-8")
        logger.info("Report generated: %s (%d articles shown)", output_path, total_shown)
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
        f"<details><summary>原文説明（英語）</summary>"
        f"<p>{original_desc}</p></details>"
    )

    # 翻訳済み説明
    if article.translated_description:
        trans_desc_html = html.escape(article.translated_description)
    else:
        trans_desc_html = '<span class="none-text">翻訳なし</span>'

    # 要約
    if article.summary:
        summary_html = (
            f'<p class="summary">{html.escape(article.summary)}</p>'
        )
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
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/test_report_generator.py -v
```

期待結果: 全10テスト PASS

- [ ] **Step 5: 型チェックと lint を確認する**

```bash
uv run mypy src/report_generator.py
uv run ruff check src/report_generator.py tests/test_report_generator.py
uv run ruff format --check src/report_generator.py tests/test_report_generator.py
```

期待結果: エラーなし。`ruff format` でフォーマットエラーが出た場合は `uv run ruff format src/report_generator.py tests/test_report_generator.py` で修正してから再確認する。

- [ ] **Step 6: コミットする**

```bash
git add src/report_generator.py tests/test_report_generator.py
git commit -m "feat: add HTML translation/summary review report generator"
```

---

### Task 2: `main.py` と `config.yaml` にレポート生成を統合する

**Files:**
- Modify: `main.py`
- Modify: `config.yaml`
- Modify: `.github/workflows/update-rss.yml`

**Interfaces:**
- Consumes（Task 1 が提供）:
  ```python
  from src.report_generator import generate_report
  # generate_report(articles: list[TranslatedArticle], output_path: str, items_per_feed: int = 10) -> None
  ```

- [ ] **Step 1: `config.yaml` に `report` セクションを追加する**

`config.yaml` の末尾に以下を追加する（既存の `cache:` セクションの後）:

```yaml
report:
  output_path: docs/report.html
  items_per_feed: 10
```

- [ ] **Step 2: `main.py` に `generate_report` のインポートと設定読み込みを追加する**

`main.py` の imports セクションに追加する:

```python
from src.report_generator import generate_report
```

`main()` 内の `cache_config` 読み込みブロックの後（`translated_cache = load_translated_cache(cache_path)` の前）に以下を追加する:

```python
report_config: dict[str, object] = config.get("report", {})  # type: ignore[assignment]
report_output_path = str(report_config.get("output_path", "docs/report.html"))
report_items_per_feed = int(str(report_config.get("items_per_feed", 10)))
```

- [ ] **Step 3: `main.py` の RSS 生成ループの後にレポート生成呼び出しを追加する**

現在の `for feed in feeds:` ループの後（`elapsed = time.time() - start` の前）に以下を追加する:

```python
try:
    generate_report(all_translated, report_output_path, items_per_feed=report_items_per_feed)
except Exception as e:
    logger.warning("Failed to generate report: %s", e)
```

- [ ] **Step 4: `update-rss.yml` のコミット対象に `docs/report.html` を追加する**

`.github/workflows/update-rss.yml` を開いて `git add` または `git diff --quiet` が使われているステップを確認し、`docs/report.html` がコミット対象に含まれるよう変更する。

現在の `update-rss.yml` の `git add` 行を確認する:

```bash
grep -n "git add\|git diff\|git commit" .github/workflows/update-rss.yml
```

`docs/feed/` や `cache/` が指定されているなら、`docs/report.html` も同じ行か直後に追加する。変更前後で `git diff` が空でも正常動作するよう確認する。

- [ ] **Step 5: 統合テストをローカルで手動確認する**

```bash
uv run python main.py
```

期待結果:
- ログに `Report generated: docs/report.html` が出力される
- `docs/report.html` が生成される
- `open docs/report.html` でブラウザに HTML が表示され、フィードごとのセクションと記事カードが確認できる

`docs/report.html` が生成されない場合は `logger.warning` の出力を確認する。

- [ ] **Step 6: 全テストが通ることを確認する**

```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run mypy src/
```

期待結果: 全テスト PASS、エラーなし

- [ ] **Step 7: コミットする**

```bash
git add main.py config.yaml .github/workflows/update-rss.yml docs/report.html
git commit -m "feat: integrate report generation into main pipeline"
```

---
