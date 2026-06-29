# RSS Feed Translator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 海外RSSフィードを定期取得し、Google Translate（機械翻訳）とOpenAI/Claude（自然な日本語化・3行要約）を組み合わせて翻訳・要約したRSSフィードをGitHub Pages で公開する。

**Architecture:** `main.py`から fetch → translate → summarize → cache → generate の5ステップパイプラインを順次実行する。各ステップは`src/`内の独立したモジュールとして実装し、翻訳エンジン・LLM要約エンジンはそれぞれ`typing.Protocol`で抽象化して差し替え可能にする。翻訳済みデータは`cache/translated.json`にGUIDキーで保存し、差分のみ処理する。

**Tech Stack:** Python 3.12+, uv, feedparser, requests, pyyaml, google-cloud-translate, openai, anthropic, deepl, pytest, responses, ruff, mypy

## Global Constraints

- Python 3.12+（`str | None`のUnion構文、`from __future__ import annotations`活用）
- uv で依存管理（`pyproject.toml` + `uv.lock`、`requirements.txt`不使用）
- 全関数・メソッドに型ヒント必須
- `logging.getLogger(__name__)`でモジュールごとのロガー取得
- カスタム例外は`src/exceptions.py`に集約
- テストは`tests/`配下、`pytest`で実行（`uv run pytest tests/ -v`）
- リンター: `uv run ruff check src/ tests/`
- 型チェック: `uv run mypy src/`
- コミットメッセージはConventional Commits形式（`feat:`, `test:`, `chore:`等）

---

## File Map

| ファイル | 責務 |
|---|---|
| `main.py` | パイプライン実行エントリポイント |
| `config.yaml` | フィード・翻訳エンジン設定 |
| `src/models.py` | データクラス（`FeedConfig`, `Article`, `TranslatedArticle`） |
| `src/exceptions.py` | カスタム例外クラス |
| `src/cache.py` | `translated.json` / `http_cache.json` の読み書き |
| `src/fetcher.py` | RSS取得（ETag/Last-Modified対応） |
| `src/translator.py` | `Translator` Protocol定義 + エンジン選択ファクトリ |
| `src/translators/google.py` | Google Translate実装 |
| `src/translators/openai.py` | OpenAI翻訳実装 |
| `src/translators/deepl.py` | DeepL実装 |
| `src/summarizer.py` | `Summarizer` Protocol定義 + エンジン選択ファクトリ |
| `src/summarizers/openai.py` | OpenAI要約実装（JSONモード） |
| `src/summarizers/claude.py` | Claude要約実装（JSONモード） |
| `src/generator.py` | RSS 2.0 XML生成 |
| `tests/conftest.py` | 共通フィクスチャ |
| `tests/test_models.py` | モデルのデータクラス検証 |
| `tests/test_cache.py` | キャッシュ読み書きテスト |
| `tests/test_fetcher.py` | RSS取得テスト（HTTPモック） |
| `tests/test_translator.py` | 翻訳エンジン抽象化テスト |
| `tests/test_summarizer.py` | 要約エンジン抽象化テスト |
| `tests/test_generator.py` | RSS XML生成テスト |
| `tests/test_pipeline.py` | パイプライン統合テスト |
| `.github/workflows/test.yml` | push時テスト実行 |
| `.github/workflows/update-rss.yml` | 30分cronでRSS更新 |

---

## Task 1: プロジェクト基盤セットアップ

**Files:**
- Create: `pyproject.toml`
- Create: `config.yaml`
- Create: `src/__init__.py`
- Create: `src/translators/__init__.py`
- Create: `src/summarizers/__init__.py`
- Create: `tests/__init__.py`
- Create: `cache/.gitkeep`
- Create: `docs/.gitkeep`
- Create: `.gitignore`

**Interfaces:**
- Produces: `uv run pytest tests/ -v` が実行できる環境

- [ ] **Step 1: uvプロジェクトを初期化する**

```bash
cd /Users/r.ishitsuka/Repositories/git/rss-feed-translator
uv init --no-workspace
```

- [ ] **Step 2: pyproject.toml を上書き作成する**

```toml
[project]
name = "rss-feed-translator"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "feedparser>=6.0",
    "requests>=2.32",
    "pyyaml>=6.0",
    "google-cloud-translate>=3.15",
    "openai>=1.50",
    "anthropic>=0.34",
    "deepl>=1.18",
    "defusedxml>=0.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "responses>=0.25",
    "mypy>=1.10",
    "ruff>=0.5",
    "types-requests",
    "types-PyYAML",
]

[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.mypy]
strict = true
python_version = "3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: 依存関係をインストールしてuv.lockを生成する**

```bash
uv sync --all-extras
```

期待: `uv.lock`が生成され、`Resolved N packages`と表示される

- [ ] **Step 4: config.yaml を作成する**

```yaml
feeds:
  - name: Ars Technica
    url: https://feeds.arstechnica.com/arstechnica/index
  - name: Hacker News
    url: https://hnrss.org/frontpage

translator:
  engine: google  # google | openai | deepl

summarizer:
  enabled: true
  engine: openai  # openai | claude
  model: gpt-4o-mini

output:
  path: docs/rss.xml
  max_items: 200

cache:
  path: cache/translated.json
  http_cache_path: cache/http_cache.json
```

- [ ] **Step 5: ディレクトリ構造を作成する**

```bash
mkdir -p src/translators src/summarizers tests cache docs
touch src/__init__.py src/translators/__init__.py src/summarizers/__init__.py
touch tests/__init__.py
touch cache/.gitkeep docs/.gitkeep
```

- [ ] **Step 6: .gitignore を作成する**

```
__pycache__/
*.pyc
.venv/
.env
*.egg-info/
.mypy_cache/
.ruff_cache/
.pytest_cache/
```

- [ ] **Step 7: pytestが動作することを確認する**

```bash
uv run pytest tests/ -v
```

期待: `no tests ran` または `collected 0 items`（エラーなし）

- [ ] **Step 8: コミットする**

```bash
git init
git add pyproject.toml uv.lock config.yaml src/ tests/ cache/.gitkeep docs/.gitkeep .gitignore
git commit -m "chore: initial project setup with uv"
```

---

## Task 2: データモデルと例外クラス

**Files:**
- Create: `src/models.py`
- Create: `src/exceptions.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces:
  - `FeedConfig(name: str, url: str)` — frozen dataclass
  - `Article(guid: str, title: str, description: str, link: str, published: datetime, source: str)` — frozen dataclass
  - `TranslatedArticle(guid, original_title, original_description, translated_title, translated_description, natural_title, summary, link, published, source, translated_at)` — dataclass（mutable）
  - `FeedFetchError`, `TranslationError`, `TranslationSkippedError`, `SummarizationError`, `SummarizationSkippedError` — 例外クラス

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_models.py`:
```python
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models import Article, FeedConfig, TranslatedArticle


def test_feed_config_is_frozen() -> None:
    config = FeedConfig(name="Test", url="https://example.com/rss")
    with pytest.raises(Exception):
        config.name = "Changed"  # type: ignore[misc]


def test_article_fields() -> None:
    now = datetime.now(tz=timezone.utc)
    article = Article(
        guid="https://example.com/1",
        title="Test Title",
        description="Test description",
        link="https://example.com/1",
        published=now,
        source="Test Feed",
    )
    assert article.guid == "https://example.com/1"
    assert article.source == "Test Feed"


def test_translated_article_optional_fields() -> None:
    now = datetime.now(tz=timezone.utc)
    article = TranslatedArticle(
        guid="https://example.com/1",
        original_title="Original",
        original_description="Desc",
        translated_title=None,
        translated_description=None,
        natural_title=None,
        summary=None,
        link="https://example.com/1",
        published=now,
        source="Test",
        translated_at=now,
    )
    assert article.translated_title is None
    assert article.natural_title is None
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_models.py -v
```

期待: `ImportError: cannot import name 'Article' from 'src.models'`

- [ ] **Step 3: src/models.py を実装する**

```python
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
```

- [ ] **Step 4: src/exceptions.py を実装する**

```python
from __future__ import annotations


class FeedFetchError(Exception):
    """RSSフィードの取得に失敗した場合"""


class TranslationError(Exception):
    """翻訳APIの呼び出しに失敗した場合"""


class TranslationSkippedError(TranslationError):
    """リトライ上限に達して翻訳をスキップした場合"""


class SummarizationError(Exception):
    """LLM要約の生成に失敗した場合"""


class SummarizationSkippedError(SummarizationError):
    """リトライ上限に達して要約をスキップした場合"""
```

- [ ] **Step 5: テストが通ることを確認する**

```bash
uv run pytest tests/test_models.py -v
```

期待: `3 passed`

- [ ] **Step 6: 型チェックを実行する**

```bash
uv run mypy src/models.py src/exceptions.py
```

期待: `Success: no issues found`

- [ ] **Step 7: コミットする**

```bash
git add src/models.py src/exceptions.py tests/test_models.py
git commit -m "feat: add data models and custom exceptions"
```

---

## Task 3: キャッシュ管理モジュール

**Files:**
- Create: `src/cache.py`
- Create: `tests/test_cache.py`

**Interfaces:**
- Consumes: `TranslatedArticle` (from `src.models`)
- Produces:
  - `load_translated_cache(path: str) -> dict[str, TranslatedArticle]`
  - `save_translated_cache(path: str, cache: dict[str, TranslatedArticle]) -> None`
  - `load_http_cache(path: str) -> dict[str, dict[str, str]]`
  - `save_http_cache(path: str, cache: dict[str, dict[str, str]]) -> None`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_cache.py`:
```python
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.cache import load_translated_cache, save_translated_cache, load_http_cache, save_http_cache
from src.models import TranslatedArticle


@pytest.fixture
def tmp_cache_path(tmp_path: Path) -> str:
    return str(tmp_path / "translated.json")


@pytest.fixture
def sample_article() -> TranslatedArticle:
    now = datetime.now(tz=timezone.utc)
    return TranslatedArticle(
        guid="https://example.com/1",
        original_title="Original",
        original_description="Desc",
        translated_title="翻訳タイトル",
        translated_description="翻訳説明",
        natural_title="自然なタイトル",
        summary="要約1行目。\n要約2行目。\n要約3行目。",
        link="https://example.com/1",
        published=now,
        source="Test",
        translated_at=now,
    )


def test_save_and_load_translated_cache(tmp_cache_path: str, sample_article: TranslatedArticle) -> None:
    cache = {sample_article.guid: sample_article}
    save_translated_cache(tmp_cache_path, cache)

    loaded = load_translated_cache(tmp_cache_path)
    assert sample_article.guid in loaded
    assert loaded[sample_article.guid].translated_title == "翻訳タイトル"
    assert loaded[sample_article.guid].natural_title == "自然なタイトル"


def test_load_translated_cache_returns_empty_when_not_exists(tmp_cache_path: str) -> None:
    result = load_translated_cache(tmp_cache_path)
    assert result == {}


def test_translated_cache_handles_null_fields(tmp_cache_path: str) -> None:
    now = datetime.now(tz=timezone.utc)
    article = TranslatedArticle(
        guid="https://example.com/2",
        original_title="Title",
        original_description="Desc",
        translated_title=None,
        translated_description=None,
        natural_title=None,
        summary=None,
        link="https://example.com/2",
        published=now,
        source="Test",
        translated_at=now,
    )
    cache = {article.guid: article}
    save_translated_cache(tmp_cache_path, cache)
    loaded = load_translated_cache(tmp_cache_path)
    assert loaded[article.guid].translated_title is None
    assert loaded[article.guid].natural_title is None


def test_save_and_load_http_cache(tmp_path: Path) -> None:
    path = str(tmp_path / "http_cache.json")
    http_cache = {
        "https://example.com/rss": {
            "etag": '"abc123"',
            "last_modified": "Mon, 29 Jun 2026 10:00:00 GMT",
        }
    }
    save_http_cache(path, http_cache)
    loaded = load_http_cache(path)
    assert loaded["https://example.com/rss"]["etag"] == '"abc123"'
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_cache.py -v
```

期待: `ImportError`

- [ ] **Step 3: src/cache.py を実装する**

```python
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from src.models import TranslatedArticle

logger = logging.getLogger(__name__)


def load_translated_cache(path: str) -> dict[str, TranslatedArticle]:
    if not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data: dict[str, dict[str, object]] = json.load(f)
    result: dict[str, TranslatedArticle] = {}
    for guid, item in data.items():
        result[guid] = TranslatedArticle(
            guid=guid,
            original_title=str(item["original_title"]),
            original_description=str(item["original_description"]),
            translated_title=item.get("translated_title") and str(item["translated_title"]) or None,  # type: ignore[arg-type]
            translated_description=item.get("translated_description") and str(item["translated_description"]) or None,  # type: ignore[arg-type]
            natural_title=item.get("natural_title") and str(item["natural_title"]) or None,  # type: ignore[arg-type]
            summary=item.get("summary") and str(item["summary"]) or None,  # type: ignore[arg-type]
            link=str(item["link"]),
            published=datetime.fromisoformat(str(item["published"])),
            source=str(item["source"]),
            translated_at=datetime.fromisoformat(str(item["translated_at"])),
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
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/test_cache.py -v
```

期待: `4 passed`

- [ ] **Step 5: 型チェックを実行する**

```bash
uv run mypy src/cache.py
```

期待: `Success: no issues found`（警告があれば修正する）

- [ ] **Step 6: コミットする**

```bash
git add src/cache.py tests/test_cache.py
git commit -m "feat: add cache management module"
```

---

## Task 4: RSSフェッチャー

**Files:**
- Create: `src/fetcher.py`
- Create: `tests/test_fetcher.py`

**Interfaces:**
- Consumes:
  - `FeedConfig` (from `src.models`)
  - `load_http_cache`, `save_http_cache` (from `src.cache`)
- Produces:
  - `fetch_feed(feed: FeedConfig, http_cache: dict[str, dict[str, str]]) -> list[Article]`
    - 取得失敗時は`FeedFetchError`を送出（呼び出し元でキャッチする）
  - `fetch_all_feeds(feeds: list[FeedConfig], http_cache: dict[str, dict[str, str]]) -> tuple[list[Article], dict[str, dict[str, str]]]`
    - 個別フィードの失敗は握り潰してログ出力し、他フィードは継続

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_fetcher.py`:
```python
from __future__ import annotations

import responses as resp_mock

from src.fetcher import fetch_feed, fetch_all_feeds
from src.models import FeedConfig
from src.exceptions import FeedFetchError
import pytest

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>Article One</title>
      <description>Description one</description>
      <link>https://example.com/1</link>
      <guid>https://example.com/1</guid>
      <pubDate>Mon, 29 Jun 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Article Two</title>
      <description>Description two</description>
      <link>https://example.com/2</link>
      <guid>https://example.com/2</guid>
      <pubDate>Mon, 29 Jun 2026 11:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


@resp_mock.activate
def test_fetch_feed_returns_articles() -> None:
    resp_mock.add(resp_mock.GET, "https://example.com/rss", body=RSS_SAMPLE, status=200)
    feed = FeedConfig(name="Test", url="https://example.com/rss")
    articles = fetch_feed(feed, http_cache={})
    assert len(articles) == 2
    assert articles[0].title == "Article One"
    assert articles[0].source == "Test"
    assert articles[0].guid == "https://example.com/1"


@resp_mock.activate
def test_fetch_feed_raises_on_http_error() -> None:
    resp_mock.add(resp_mock.GET, "https://example.com/rss", status=500)
    feed = FeedConfig(name="Test", url="https://example.com/rss")
    with pytest.raises(FeedFetchError):
        fetch_feed(feed, http_cache={})


@resp_mock.activate
def test_fetch_feed_uses_etag() -> None:
    resp_mock.add(resp_mock.GET, "https://example.com/rss", status=304)
    feed = FeedConfig(name="Test", url="https://example.com/rss")
    http_cache = {"https://example.com/rss": {"etag": '"abc"', "last_modified": ""}}
    articles = fetch_feed(feed, http_cache=http_cache)
    assert articles == []


@resp_mock.activate
def test_fetch_all_feeds_continues_on_failure() -> None:
    resp_mock.add(resp_mock.GET, "https://example.com/good", body=RSS_SAMPLE, status=200)
    resp_mock.add(resp_mock.GET, "https://example.com/bad", status=500)
    feeds = [
        FeedConfig(name="Good", url="https://example.com/good"),
        FeedConfig(name="Bad", url="https://example.com/bad"),
    ]
    articles, _ = fetch_all_feeds(feeds, http_cache={})
    assert len(articles) == 2  # goodフィードの2件のみ取得
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_fetcher.py -v
```

期待: `ImportError`

- [ ] **Step 3: src/fetcher.py を実装する**

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser
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
        raise FeedFetchError(
            f"HTTP {response.status_code} fetching {feed.url}"
        )

    if response.headers.get("ETag"):
        http_cache.setdefault(feed.url, {})["etag"] = response.headers["ETag"]
    if response.headers.get("Last-Modified"):
        http_cache.setdefault(feed.url, {})["last_modified"] = response.headers["Last-Modified"]

    parsed = feedparser.parse(response.text)
    articles: list[Article] = []
    for entry in parsed.entries:
        guid: str = getattr(entry, "id", None) or getattr(entry, "link", "")
        title: str = getattr(entry, "title", "")
        description: str = getattr(entry, "summary", "") or getattr(entry, "description", "")
        link: str = getattr(entry, "link", "")
        published_parsed = getattr(entry, "published_parsed", None)
        if published_parsed:
            published = datetime(*published_parsed[:6], tzinfo=timezone.utc)
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
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/test_fetcher.py -v
```

期待: `4 passed`

- [ ] **Step 5: 型チェックを実行する**

```bash
uv run mypy src/fetcher.py
```

期待: `Success: no issues found`

- [ ] **Step 6: コミットする**

```bash
git add src/fetcher.py tests/test_fetcher.py
git commit -m "feat: add RSS fetcher with ETag/Last-Modified support"
```

---

## Task 5: 翻訳エンジン抽象化と実装

**Files:**
- Create: `src/translator.py`
- Create: `src/translators/google.py`
- Create: `src/translators/openai.py`
- Create: `src/translators/deepl.py`
- Create: `tests/test_translator.py`

**Interfaces:**
- Consumes: `TranslationError`, `TranslationSkippedError` (from `src.exceptions`)
- Produces:
  - `Translator` Protocol: `translate(texts: list[str], target_lang: str = "ja") -> list[str]`
  - `get_translator(engine: str) -> Translator`
  - `translate_articles(articles: list[Article], translator: Translator) -> list[tuple[str, str]]`
    - 戻り値: `[(translated_title, translated_description), ...]`（記事順と対応）
  - `with_retry(fn: Callable[[], T], max_attempts: int = 3) -> T`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_translator.py`:
```python
from __future__ import annotations

import pytest

from src.translator import get_translator, with_retry, translate_articles
from src.exceptions import TranslationError, TranslationSkippedError
from src.models import Article
from datetime import datetime, timezone


class MockTranslator:
    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        return [f"翻訳: {t}" for t in texts]


class FailingTranslator:
    def __init__(self, fail_times: int = 3) -> None:
        self.calls = 0
        self.fail_times = fail_times

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise TranslationError("API error")
        return [f"翻訳: {t}" for t in texts]


def make_article(n: int) -> Article:
    return Article(
        guid=f"https://example.com/{n}",
        title=f"Title {n}",
        description=f"Description {n}",
        link=f"https://example.com/{n}",
        published=datetime.now(tz=timezone.utc),
        source="Test",
    )


def test_mock_translator_returns_translated_texts() -> None:
    translator = MockTranslator()
    result = translator.translate(["Hello", "World"])
    assert result == ["翻訳: Hello", "翻訳: World"]


def test_with_retry_succeeds_on_second_attempt() -> None:
    calls = 0
    def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise TranslationError("fail")
        return "ok"
    result = with_retry(flaky, max_attempts=3)
    assert result == "ok"
    assert calls == 2


def test_with_retry_raises_after_max_attempts() -> None:
    def always_fail() -> str:
        raise TranslationError("fail")
    with pytest.raises(TranslationSkippedError):
        with_retry(always_fail, max_attempts=3)


def test_translate_articles_batches_correctly() -> None:
    translator = MockTranslator()
    articles = [make_article(1), make_article(2)]
    results = translate_articles(articles, translator)
    assert len(results) == 2
    assert results[0] == ("翻訳: Title 1", "翻訳: Description 1")
    assert results[1] == ("翻訳: Title 2", "翻訳: Description 2")


def test_get_translator_raises_on_unknown_engine() -> None:
    with pytest.raises(ValueError, match="Unknown translator engine"):
        get_translator("unknown")
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_translator.py -v
```

期待: `ImportError`

- [ ] **Step 3: src/translator.py を実装する**

```python
from __future__ import annotations

import logging
import time
from typing import Callable, Protocol, TypeVar

from src.exceptions import TranslationError, TranslationSkippedError
from src.models import Article

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Translator(Protocol):
    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        ...


def with_retry(fn: Callable[[], T], max_attempts: int = 3) -> T:
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except TranslationError as e:
            if attempt == max_attempts:
                logger.error("Translation failed after %d attempts: %s", max_attempts, e)
                raise TranslationSkippedError(str(e)) from e
            wait = 2 ** (attempt - 1)
            logger.warning("Translation attempt %d/%d failed, retrying in %ds: %s", attempt, max_attempts, wait, e)
            time.sleep(wait)
    raise TranslationSkippedError("Unreachable")


def translate_articles(articles: list[Article], translator: Translator) -> list[tuple[str, str]]:
    titles = [a.title for a in articles]
    descriptions = [a.description for a in articles]
    all_texts = titles + descriptions

    def _translate() -> list[str]:
        return translator.translate(all_texts)

    translated = with_retry(_translate)
    mid = len(articles)
    return list(zip(translated[:mid], translated[mid:]))


def get_translator(engine: str) -> Translator:
    if engine == "google":
        from src.translators.google import GoogleTranslator
        return GoogleTranslator()
    if engine == "openai":
        from src.translators.openai import OpenAITranslator
        return OpenAITranslator()
    if engine == "deepl":
        from src.translators.deepl import DeepLTranslator
        return DeepLTranslator()
    raise ValueError(f"Unknown translator engine: {engine!r}. Choose from: google, openai, deepl")
```

- [ ] **Step 4: src/translators/google.py を実装する**

```python
from __future__ import annotations

import logging
import os

from src.exceptions import TranslationError

logger = logging.getLogger(__name__)


class GoogleTranslator:
    def __init__(self) -> None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY environment variable not set")
        try:
            from google.cloud import translate_v2 as google_translate
            self._client = google_translate.Client(client_options={"api_key": api_key})
        except Exception as e:
            raise TranslationError(f"Failed to initialize Google Translate client: {e}") from e

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        if not texts:
            return []
        try:
            results = self._client.translate(texts, target_language=target_lang)
            return [r["translatedText"] for r in results]
        except Exception as e:
            raise TranslationError(f"Google Translate API error: {e}") from e
```

- [ ] **Step 5: src/translators/openai.py を実装する**

```python
from __future__ import annotations

import logging
import os

from src.exceptions import TranslationError

logger = logging.getLogger(__name__)


class OpenAITranslator:
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set")
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
        except Exception as e:
            raise TranslationError(f"Failed to initialize OpenAI client: {e}") from e

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        if not texts:
            return []
        joined = "\n---\n".join(texts)
        prompt = (
            f"Translate each section separated by '---' into {target_lang}. "
            "Return only the translations separated by '\\n---\\n', in the same order. "
            "Do not add any explanation.\n\n" + joined
        )
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content or ""
            return [t.strip() for t in content.split("---")]
        except Exception as e:
            raise TranslationError(f"OpenAI translation error: {e}") from e
```

- [ ] **Step 6: src/translators/deepl.py を実装する**

```python
from __future__ import annotations

import logging
import os

from src.exceptions import TranslationError

logger = logging.getLogger(__name__)


class DeepLTranslator:
    def __init__(self) -> None:
        api_key = os.environ.get("DEEPL_API_KEY")
        if not api_key:
            raise EnvironmentError("DEEPL_API_KEY environment variable not set")
        try:
            import deepl
            self._translator = deepl.Translator(api_key)
        except Exception as e:
            raise TranslationError(f"Failed to initialize DeepL client: {e}") from e

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        if not texts:
            return []
        try:
            results = self._translator.translate_text(texts, target_lang=target_lang.upper())
            return [r.text for r in results]
        except Exception as e:
            raise TranslationError(f"DeepL API error: {e}") from e
```

- [ ] **Step 7: テストが通ることを確認する**

```bash
uv run pytest tests/test_translator.py -v
```

期待: `5 passed`

- [ ] **Step 8: コミットする**

```bash
git add src/translator.py src/translators/ tests/test_translator.py
git commit -m "feat: add translator protocol and engine implementations"
```

---

## Task 6: LLM要約エンジン抽象化と実装

**Files:**
- Create: `src/summarizer.py`
- Create: `src/summarizers/openai.py`
- Create: `src/summarizers/claude.py`
- Create: `tests/test_summarizer.py`

**Interfaces:**
- Consumes: `Article` (from `src.models`), `SummarizationError`, `SummarizationSkippedError` (from `src.exceptions`)
- Produces:
  - `Summarizer` Protocol: `summarize(article: Article) -> tuple[str, str]`（`(natural_title, summary)`）
  - `get_summarizer(engine: str, model: str, prompt_template: str) -> Summarizer`
  - `summarize_with_retry(summarizer: Summarizer, article: Article, max_attempts: int = 3) -> tuple[str, str] | tuple[None, None]`
    - 失敗時は`(None, None)`を返す

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_summarizer.py`:
```python
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.exceptions import SummarizationError
from src.models import Article
from src.summarizer import get_summarizer, summarize_with_retry


class MockSummarizer:
    def summarize(self, article: Article) -> tuple[str, str]:
        return (f"自然: {article.title}", f"要約: {article.description}")


class FailingSummarizer:
    def summarize(self, article: Article) -> tuple[str, str]:
        raise SummarizationError("API error")


def make_article() -> Article:
    return Article(
        guid="https://example.com/1",
        title="AI Breakthrough",
        description="Researchers found a new approach.",
        link="https://example.com/1",
        published=datetime.now(tz=timezone.utc),
        source="Ars Technica",
    )


def test_mock_summarizer_returns_tuple() -> None:
    article = make_article()
    result = MockSummarizer().summarize(article)
    assert result == ("自然: AI Breakthrough", "要約: Researchers found a new approach.")


def test_summarize_with_retry_returns_none_on_failure() -> None:
    article = make_article()
    result = summarize_with_retry(FailingSummarizer(), article, max_attempts=3)
    assert result == (None, None)


def test_summarize_with_retry_succeeds() -> None:
    article = make_article()
    result = summarize_with_retry(MockSummarizer(), article, max_attempts=3)
    assert result[0] is not None
    assert result[1] is not None


def test_get_summarizer_raises_on_unknown_engine() -> None:
    with pytest.raises(ValueError, match="Unknown summarizer engine"):
        get_summarizer("unknown", "model", "prompt")
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_summarizer.py -v
```

期待: `ImportError`

- [ ] **Step 3: src/summarizer.py を実装する**

```python
from __future__ import annotations

import logging
import time
from typing import Protocol

from src.exceptions import SummarizationError, SummarizationSkippedError
from src.models import Article

logger = logging.getLogger(__name__)


class Summarizer(Protocol):
    def summarize(self, article: Article) -> tuple[str, str]:
        ...


def summarize_with_retry(
    summarizer: Summarizer,
    article: Article,
    max_attempts: int = 3,
) -> tuple[str, str] | tuple[None, None]:
    for attempt in range(1, max_attempts + 1):
        try:
            return summarizer.summarize(article)
        except SummarizationError as e:
            if attempt == max_attempts:
                logger.error("Summarization failed after %d attempts for %s: %s", max_attempts, article.guid, e)
                return (None, None)
            wait = 2 ** (attempt - 1)
            logger.warning("Summarization attempt %d/%d failed, retrying in %ds", attempt, max_attempts, wait)
            time.sleep(wait)
    return (None, None)


def get_summarizer(engine: str, model: str, prompt_template: str) -> Summarizer:
    if engine == "openai":
        from src.summarizers.openai import OpenAISummarizer
        return OpenAISummarizer(model=model, prompt_template=prompt_template)
    if engine == "claude":
        from src.summarizers.claude import ClaudeSummarizer
        return ClaudeSummarizer(model=model, prompt_template=prompt_template)
    raise ValueError(f"Unknown summarizer engine: {engine!r}. Choose from: openai, claude")
```

- [ ] **Step 4: src/summarizers/openai.py を実装する**

```python
from __future__ import annotations

import json
import logging
import os

from src.exceptions import SummarizationError
from src.models import Article

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = """以下の英語のITニュース記事のタイトルと概要を読み、次のJSONを返してください。
{
  "natural_title": "自然な日本語タイトル（直訳でなく読みやすく）",
  "summary": "1行目の要約。\\n2行目の要約。\\n3行目の要約。"
}
タイトル: {title}
概要: {description}
ソース: {source}"""


class OpenAISummarizer:
    def __init__(self, model: str = "gpt-4o-mini", prompt_template: str = DEFAULT_PROMPT) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set")
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._prompt_template = prompt_template

    def summarize(self, article: Article) -> tuple[str, str]:
        prompt = self._prompt_template.format(
            title=article.title,
            description=article.description,
            source=article.source,
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            natural_title: str = data.get("natural_title", "")
            summary: str = data.get("summary", "")
            if not natural_title or not summary:
                raise SummarizationError("Empty response from OpenAI summarizer")
            return (natural_title, summary)
        except SummarizationError:
            raise
        except Exception as e:
            raise SummarizationError(f"OpenAI summarization error: {e}") from e
```

- [ ] **Step 5: src/summarizers/claude.py を実装する**

```python
from __future__ import annotations

import json
import logging
import os

from src.exceptions import SummarizationError
from src.models import Article

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = """以下の英語のITニュース記事のタイトルと概要を読み、次のJSONを返してください。
{
  "natural_title": "自然な日本語タイトル（直訳でなく読みやすく）",
  "summary": "1行目の要約。\\n2行目の要約。\\n3行目の要約。"
}
タイトル: {title}
概要: {description}
ソース: {source}"""


class ClaudeSummarizer:
    def __init__(self, model: str = "claude-haiku-4-5-20251001", prompt_template: str = DEFAULT_PROMPT) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set")
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._prompt_template = prompt_template

    def summarize(self, article: Article) -> tuple[str, str]:
        prompt = self._prompt_template.format(
            title=article.title,
            description=article.description,
            source=article.source,
        )
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text if response.content else "{}"
            start = content.find("{")
            end = content.rfind("}") + 1
            data = json.loads(content[start:end])
            natural_title: str = data.get("natural_title", "")
            summary: str = data.get("summary", "")
            if not natural_title or not summary:
                raise SummarizationError("Empty response from Claude summarizer")
            return (natural_title, summary)
        except SummarizationError:
            raise
        except Exception as e:
            raise SummarizationError(f"Claude summarization error: {e}") from e
```

- [ ] **Step 6: テストが通ることを確認する**

```bash
uv run pytest tests/test_summarizer.py -v
```

期待: `4 passed`

- [ ] **Step 7: コミットする**

```bash
git add src/summarizer.py src/summarizers/ tests/test_summarizer.py
git commit -m "feat: add summarizer protocol with OpenAI and Claude implementations"
```

---

## Task 7: RSS生成モジュール

**Files:**
- Create: `src/generator.py`
- Create: `tests/test_generator.py`

**Interfaces:**
- Consumes: `TranslatedArticle` (from `src.models`)
- Produces:
  - `generate_rss(articles: list[TranslatedArticle], output_path: str, max_items: int = 200) -> None`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_generator.py`:
```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import defusedxml.ElementTree as ET
import pytest

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


def test_generate_rss_uses_natural_title_when_available(tmp_path: Path) -> None:
    output = str(tmp_path / "rss.xml")
    articles = [make_translated_article(1, natural_title="自然なタイトル", summary="要約文")]
    generate_rss(articles, output)

    tree = ET.parse(output)
    root = tree.getroot()
    title_el = root.find("./channel/item/title")
    assert title_el is not None
    assert title_el.text == "自然なタイトル"


def test_generate_rss_falls_back_to_translated_title(tmp_path: Path) -> None:
    output = str(tmp_path / "rss.xml")
    articles = [make_translated_article(1, natural_title=None)]
    generate_rss(articles, output)

    tree = ET.parse(output)
    root = tree.getroot()
    title_el = root.find("./channel/item/title")
    assert title_el is not None
    assert title_el.text == "翻訳タイトル 1"


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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_generator.py -v
```

期待: `ImportError`

- [ ] **Step 3: src/generator.py を実装する**

```python
from __future__ import annotations

import logging
from datetime import timezone
from email.utils import format_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import defusedxml.ElementTree as defused_ET

from src.models import TranslatedArticle

logger = logging.getLogger(__name__)


def generate_rss(
    articles: list[TranslatedArticle],
    output_path: str,
    max_items: int = 200,
) -> None:
    sorted_articles = sorted(articles, key=lambda a: a.published, reverse=True)[:max_items]

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "RSS Feed Translator"
    ET.SubElement(channel, "description").text = "海外ITニュースの日本語翻訳フィード"
    ET.SubElement(channel, "link").text = "https://github.com"

    for article in sorted_articles:
        item = ET.SubElement(channel, "item")

        display_title = article.natural_title or article.translated_title or article.original_title
        ET.SubElement(item, "title").text = display_title

        display_description = article.summary or article.translated_description or article.original_description
        ET.SubElement(item, "description").text = display_description

        ET.SubElement(item, "link").text = article.link

        pub_date = article.published
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        ET.SubElement(item, "pubDate").text = format_datetime(pub_date)

        ET.SubElement(item, "source").text = article.source
        ET.SubElement(item, "guid", isPermaLink="false").text = article.guid

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    logger.info("RSS generated: %s (%d articles total)", output_path, len(sorted_articles))
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/test_generator.py -v
```

期待: `5 passed`

- [ ] **Step 5: コミットする**

```bash
git add src/generator.py tests/test_generator.py
git commit -m "feat: add RSS 2.0 XML generator"
```

---

## Task 8: メインパイプラインとconftest

**Files:**
- Create: `main.py`
- Create: `tests/conftest.py`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: 全モジュール（`src/fetcher.py`, `src/translator.py`, `src/summarizer.py`, `src/cache.py`, `src/generator.py`）
- Produces: パイプライン実行（`main.py`を`uv run python main.py`で実行できる）

- [ ] **Step 1: tests/conftest.py を作成する**

```python
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models import Article, FeedConfig, TranslatedArticle


@pytest.fixture
def sample_feed_config() -> FeedConfig:
    return FeedConfig(name="Test Feed", url="https://example.com/rss")


@pytest.fixture
def sample_article() -> Article:
    return Article(
        guid="https://example.com/1",
        title="Test Article",
        description="Test description",
        link="https://example.com/1",
        published=datetime(2026, 6, 29, 10, 0, 0, tzinfo=timezone.utc),
        source="Test Feed",
    )


@pytest.fixture
def sample_translated_article() -> TranslatedArticle:
    now = datetime(2026, 6, 29, 10, 5, 0, tzinfo=timezone.utc)
    return TranslatedArticle(
        guid="https://example.com/1",
        original_title="Test Article",
        original_description="Test description",
        translated_title="テスト記事",
        translated_description="テスト説明",
        natural_title="自然なテスト記事タイトル",
        summary="要約1行目。\n要約2行目。\n要約3行目。",
        link="https://example.com/1",
        published=datetime(2026, 6, 29, 10, 0, 0, tzinfo=timezone.utc),
        source="Test Feed",
        translated_at=now,
    )
```

- [ ] **Step 2: tests/test_pipeline.py を作成する**

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses as resp_mock

from src.models import Article, FeedConfig, TranslatedArticle


RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>New Article</title>
      <description>New description</description>
      <link>https://example.com/new</link>
      <guid>https://example.com/new</guid>
      <pubDate>Mon, 29 Jun 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


@resp_mock.activate
def test_pipeline_skips_cached_articles(tmp_path: Path) -> None:
    """キャッシュ済みGUIDの記事は翻訳をスキップする"""
    from src.cache import save_translated_cache, load_translated_cache
    from src.fetcher import fetch_all_feeds
    from src.models import FeedConfig

    cache_path = str(tmp_path / "translated.json")
    now = datetime.now(tz=timezone.utc)
    existing = TranslatedArticle(
        guid="https://example.com/new",
        original_title="New Article",
        original_description="New description",
        translated_title="新しい記事",
        translated_description="新しい説明",
        natural_title=None,
        summary=None,
        link="https://example.com/new",
        published=now,
        source="Test Feed",
        translated_at=now,
    )
    save_translated_cache(cache_path, {existing.guid: existing})

    resp_mock.add(resp_mock.GET, "https://example.com/rss", body=RSS_SAMPLE, status=200)
    feeds = [FeedConfig(name="Test Feed", url="https://example.com/rss")]
    articles, _ = fetch_all_feeds(feeds, http_cache={})

    cache = load_translated_cache(cache_path)
    new_articles = [a for a in articles if a.guid not in cache]
    assert len(new_articles) == 0  # 既にキャッシュ済み
```

- [ ] **Step 3: テストが通ることを確認する**

```bash
uv run pytest tests/test_pipeline.py -v
```

期待: `1 passed`

- [ ] **Step 4: main.py を実装する**

```python
from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from src.cache import load_http_cache, load_translated_cache, save_http_cache, save_translated_cache
from src.exceptions import TranslationSkippedError
from src.fetcher import fetch_all_feeds
from src.generator import generate_rss
from src.models import FeedConfig, TranslatedArticle
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

    config = load_config()

    feeds_config: list[dict[str, str]] = config.get("feeds", [])  # type: ignore[assignment]
    feeds = [FeedConfig(name=f["name"], url=f["url"]) for f in feeds_config]

    translator_config: dict[str, str] = config.get("translator", {})  # type: ignore[assignment]
    translator_engine = translator_config.get("engine", "google")

    summarizer_config: dict[str, object] = config.get("summarizer", {})  # type: ignore[assignment]
    summarizer_enabled = bool(summarizer_config.get("enabled", False))
    summarizer_engine = str(summarizer_config.get("engine", "openai"))
    summarizer_model = str(summarizer_config.get("model", "gpt-4o-mini"))
    summarizer_prompt = str(summarizer_config.get("prompt", ""))

    output_config: dict[str, object] = config.get("output", {})  # type: ignore[assignment]
    output_path = str(output_config.get("path", "docs/rss.xml"))
    max_items = int(output_config.get("max_items", 200))

    cache_config: dict[str, str] = config.get("cache", {})  # type: ignore[assignment]
    cache_path = cache_config.get("path", "cache/translated.json")
    http_cache_path = cache_config.get("http_cache_path", "cache/http_cache.json")

    translated_cache = load_translated_cache(cache_path)
    http_cache = load_http_cache(http_cache_path)

    logger.info("Fetching %d feeds...", len(feeds))
    all_articles, http_cache = fetch_all_feeds(feeds, http_cache)

    new_articles = [a for a in all_articles if a.guid not in translated_cache]
    logger.info(
        "Fetched %d total articles, %d new", len(all_articles), len(new_articles)
    )

    translated_count = 0
    skipped_count = 0
    error_count = 0

    if new_articles:
        translator = get_translator(translator_engine)
        logger.info(
            "Translating %d articles (engine=%s)...", len(new_articles), translator_engine
        )
        try:
            results = translate_articles(new_articles, translator)
        except TranslationSkippedError as e:
            logger.error("Batch translation failed: %s", e)
            results = [("", "")] * len(new_articles)
            error_count += len(new_articles)

        now = datetime.now(tz=timezone.utc)
        for article, (translated_title, translated_description) in zip(new_articles, results):
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
        summarizer = get_summarizer(summarizer_engine, summarizer_model, summarizer_prompt)
        to_summarize = [
            translated_cache[a.guid]
            for a in new_articles
            if a.guid in translated_cache and translated_cache[a.guid].translated_title
        ]
        logger.info(
            "Summarizing %d articles with LLM (summarizer=%s/%s)...",
            len(to_summarize),
            summarizer_engine,
            summarizer_model,
        )
        for cached_article in to_summarize:
            from src.models import Article
            source_article = Article(
                guid=cached_article.guid,
                title=cached_article.original_title,
                description=cached_article.original_description,
                link=cached_article.link,
                published=cached_article.published,
                source=cached_article.source,
            )
            natural_title, summary = summarize_with_retry(summarizer, source_article)
            if natural_title:
                cached_article.natural_title = natural_title
                cached_article.summary = summary
                summarized_count += 1
            else:
                error_count += 1
        logger.info("Summarized: %d articles", summarized_count)

    save_translated_cache(cache_path, translated_cache)
    save_http_cache(http_cache_path, http_cache)

    all_translated = list(translated_cache.values())
    generate_rss(all_translated, output_path, max_items=max_items)

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
```

- [ ] **Step 5: 全テストが通ることを確認する**

```bash
uv run pytest tests/ -v
```

期待: 全テストがパス（テスト数はTask 2〜7の合計）

- [ ] **Step 6: リンターと型チェックを実行する**

```bash
uv run ruff check src/ tests/
uv run mypy src/
```

期待: エラーなし（警告があれば修正する）

- [ ] **Step 7: コミットする**

```bash
git add main.py tests/conftest.py tests/test_pipeline.py
git commit -m "feat: add main pipeline orchestrator"
```

---

## Task 9: GitHub Actionsワークフロー

**Files:**
- Create: `.github/workflows/test.yml`
- Create: `.github/workflows/update-rss.yml`

**Interfaces:**
- Produces: GitHub Actionsでのテスト自動実行とRSS更新の自動化

- [ ] **Step 1: .github/workflows/test.yml を作成する**

```bash
mkdir -p .github/workflows
```

`.github/workflows/test.yml`:
```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Run tests
        run: uv run pytest tests/ -v
      - name: Lint
        run: uv run ruff check src/ tests/
      - name: Type check
        run: uv run mypy src/
```

- [ ] **Step 2: .github/workflows/update-rss.yml を作成する**

`.github/workflows/update-rss.yml`:
```yaml
name: Update RSS

on:
  schedule:
    - cron: '*/30 * * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v5
      - name: Install dependencies
        run: uv sync
      - name: Run pipeline
        run: uv run python main.py
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          DEEPL_API_KEY: ${{ secrets.DEEPL_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add cache/ docs/rss.xml
          git diff --staged --quiet || git commit -m "chore: update RSS feed"
          git push
```

- [ ] **Step 3: コミットする**

```bash
git add .github/
git commit -m "chore: add GitHub Actions workflows for test and RSS update"
```

---

## Task 10: 最終検証

- [ ] **Step 1: 全テストスイートを実行する**

```bash
uv run pytest tests/ -v --tb=short
```

期待: 全テストがパス

- [ ] **Step 2: リンターと型チェックを実行する**

```bash
uv run ruff check src/ tests/
uv run mypy src/
```

期待: エラーなし

- [ ] **Step 3: ローカルでパイプラインをドライラン確認する（オプション）**

実際のAPIキーが設定されている場合:
```bash
export GOOGLE_API_KEY=your_key
uv run python main.py
```

期待: `[INFO] Done in X.Xs | fetched=N new=N translated=N summarized=N errors=0`

- [ ] **Step 4: README.md を作成する（省略可）**

ユーザーが後から作成する場合はスキップ。

- [ ] **Step 5: 最終コミット**

```bash
git add -A
git diff --staged --quiet || git commit -m "chore: finalize project structure"
```
