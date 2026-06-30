# Daily Character Budget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Google Translate の1日あたりの翻訳文字数を15,000文字に制限し、超過分は翻訳せずに英語のまま RSS に含め翌日再翻訳できるようにする。

**Architecture:** `src/daily_budget.py` に `DailyBudget` クラスを新設し、`cache/char_usage.json` で日次消費文字数を永続化する。`main.py` の翻訳ループで各記事の翻訳前にバジェットを確認し、超過した記事はキャッシュに保存せず RSS 生成にのみ含める。

**Tech Stack:** Python 3.12+, pytest, ruff, mypy (strict)

## Global Constraints

- Python 3.12 以上必須
- `uv run pytest tests/ -v` でテスト実行
- `uv run ruff check src/ tests/` でリント
- `uv run mypy src/` で型チェック（strict モード）
- コミットメッセージは Conventional Commits に従う
- キャッシュファイルはすべて `cache/` 以下に配置し git コミット対象とする
- APIキーは環境変数で管理。コードやconfigファイルにハードコードしない

---

## ファイル一覧

| 操作 | パス | 役割 |
|------|------|------|
| 新規作成 | `src/daily_budget.py` | DailyBudget クラス |
| 新規作成 | `tests/test_daily_budget.py` | DailyBudget のテスト |
| 変更 | `main.py` | バジェット確認・超過スキップロジック |
| 変更 | `config.yaml` | `daily_char_limit` / `char_usage_path` 追加 |
| 新規作成 | `cache/char_usage.json` | 日次文字数バジェット初期ファイル |

---

### Task 1: DailyBudget クラスを実装する

**Files:**
- Create: `src/daily_budget.py`
- Create: `tests/test_daily_budget.py`

**Interfaces:**
- Consumes: なし
- Produces:
  - `DailyBudget(path: str, limit: int)` — コンストラクタ
  - `.remaining() -> int` — 残り利用可能文字数
  - `.can_translate(char_count: int) -> bool` — 翻訳可能かどうか
  - `.consume(char_count: int) -> None` — 文字数を消費してファイルに永続化
  - `cache/char_usage.json` の構造: `{"date": "2026-06-30", "used": 5000}`

- [ ] **Step 1: テストファイルを作成する**

`tests/test_daily_budget.py` を以下の内容で作成する:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from src.daily_budget import DailyBudget


@pytest.fixture
def budget_path(tmp_path: Path) -> str:
    return str(tmp_path / "char_usage.json")


def test_remaining_returns_full_limit_when_no_file(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    assert budget.remaining() == 15000


def test_can_translate_returns_true_when_within_limit(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    assert budget.can_translate(100) is True


def test_can_translate_returns_false_when_over_limit(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=100)
    budget.consume(100)
    assert budget.can_translate(1) is False


def test_consume_reduces_remaining(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    budget.consume(3000)
    assert budget.remaining() == 12000


def test_consume_persists_to_file(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    budget.consume(5000)
    # 別インスタンスで読み直しても値が保持される
    budget2 = DailyBudget(path=budget_path, limit=15000)
    assert budget2.remaining() == 10000


def test_daily_reset_when_date_changes(budget_path: str, tmp_path: Path) -> None:
    import json

    # 昨日の日付でファイルを作成
    with open(budget_path, "w") as f:
        json.dump({"date": "2000-01-01", "used": 9000}, f)

    budget = DailyBudget(path=budget_path, limit=15000)
    # 日付が変わっているので used がリセットされる
    assert budget.remaining() == 15000


def test_consume_multiple_times(budget_path: str) -> None:
    budget = DailyBudget(path=budget_path, limit=15000)
    budget.consume(1000)
    budget.consume(2000)
    assert budget.remaining() == 12000
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_daily_budget.py -v
```

期待: `ImportError: cannot import name 'DailyBudget'` またはモジュールが存在しないエラー

- [ ] **Step 3: DailyBudget クラスを実装する**

`src/daily_budget.py` を以下の内容で作成する:

```python
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DailyBudget:
    path: str
    limit: int
    _used: int = field(default=0, init=False, repr=False)
    _loaded: bool = field(default=False, init=False, repr=False)

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        p = Path(self.path)
        if not p.exists():
            self._used = 0
            return
        with open(self.path, encoding="utf-8") as f:
            data: dict[str, object] = json.load(f)
        today = date.today().isoformat()
        if data.get("date") != today:
            logger.info("Daily budget reset (date changed from %s to %s)", data.get("date"), today)
            self._used = 0
            return
        self._used = int(str(data.get("used", 0)))

    def remaining(self) -> int:
        self._load()
        return max(0, self.limit - self._used)

    def can_translate(self, char_count: int) -> bool:
        return self.remaining() >= char_count

    def consume(self, char_count: int) -> None:
        self._load()
        self._used += char_count
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"date": today, "used": self._used}, f, ensure_ascii=False)
        logger.debug("DailyBudget consumed %d chars, total=%d/%d", char_count, self._used, self.limit)
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/test_daily_budget.py -v
```

期待: 全テスト PASS

- [ ] **Step 5: 型チェックとリントを確認する**

```bash
uv run mypy src/daily_budget.py
uv run ruff check src/daily_budget.py tests/test_daily_budget.py
```

期待: エラーなし

- [ ] **Step 6: コミットする**

```bash
git add src/daily_budget.py tests/test_daily_budget.py
git commit -m "feat: add DailyBudget class for daily character limit tracking"
```

---

### Task 2: config.yaml と main.py にバジェット設定を追加する

**Files:**
- Modify: `config.yaml`
- Modify: `main.py`
- Create: `cache/char_usage.json`

**Interfaces:**
- Consumes:
  - `DailyBudget(path: str, limit: int)`
  - `.can_translate(char_count: int) -> bool`
  - `.consume(char_count: int) -> None`
  - `translate_articles(articles, translator) -> list[tuple[str, str]]` — 既存
- Produces:
  - バジェット超過記事はキャッシュに保存されず、翌日再翻訳される
  - バジェット超過記事は `translated_title=None` の `TranslatedArticle` として RSS 生成に渡される

- [ ] **Step 1: config.yaml にバジェット設定を追加する**

`config.yaml` の `translator` セクションと `cache` セクションを以下のように変更する:

```yaml
translator:
  engine: google   # google | openai | deepl | claude
  # provider: anthropic  # anthropic (default) | bedrock（google / openai / deepl には不要）
  daily_char_limit: 15000  # Google Translate 使用時のみ有効。省略時は無制限

cache:
  path: cache/translated.json
  http_cache_path: cache/http_cache.json
  char_usage_path: cache/char_usage.json
```

- [ ] **Step 2: cache/char_usage.json の初期ファイルを作成する**

```bash
mkdir -p cache
echo '{"date": "1970-01-01", "used": 0}' > cache/char_usage.json
```

- [ ] **Step 3: main.py にバジェットロジックを追加する**

`main.py` を以下のように変更する（差分で示す）:

**インポートを追加**（`from src.cache import ...` の直後に追記）:
```python
from src.daily_budget import DailyBudget
```

**キャッシュ設定読み込み部分を変更**（`http_cache_path = ...` の直後に追記）:
```python
char_usage_path = cache_config.get("char_usage_path", "cache/char_usage.json")
```

**translator_config の読み込み部分に追記**（`translator_provider = ...` の直後に追記）:
```python
daily_char_limit: int | None = (
    int(str(translator_config["daily_char_limit"]))
    if "daily_char_limit" in translator_config
    else None
)
```

**翻訳ループ全体を置き換える**（`if new_articles:` ブロックの `if translator is not None:` 内）:

現在の翻訳ループ（`results = translate_articles(...)` から `logger.info("Translated: ...")` まで）を以下に置き換える:

```python
        if translator is not None:
            # バジェット超過でスキップした記事（キャッシュ保存しない）
            budget_skipped: list[Article] = []
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
                        "Daily character budget exceeded (%d/%d used): skipping %d articles",
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
                    logger.error("Batch translation failed, skipping cache write: %s", e)
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
```

また、`main.py` の先頭近くの `from src.translator import` 行から `_MAX_DESCRIPTION_CHARS` が使えるよう、以下のように変更する:

```python
from src.translator import _MAX_DESCRIPTION_CHARS, get_translator, translate_articles
```

**バジェットスキップ記事を RSS 生成に含める**: `budget_skipped` の記事を `all_translated` に追加するため、`all_translated = list(translated_cache.values())` の直前に以下を追加する:

```python
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
```

（既存の `all_translated = list(translated_cache.values())` は削除する）

また `budget_skipped` は `new_articles` ブロックの外でも参照されるため、`new_articles` ブロックに入る前に初期化しておく:

```python
    budget_skipped: list[Article] = []
```

- [ ] **Step 4: 既存のテストが通ることを確認する**

```bash
uv run pytest tests/ -v
```

期待: 全テスト PASS（test_daily_budget.py を含む）

- [ ] **Step 5: 型チェックとリントを確認する**

```bash
uv run mypy src/
uv run ruff check src/ tests/
```

期待: エラーなし

- [ ] **Step 6: コミットする**

```bash
git add config.yaml cache/char_usage.json main.py
git commit -m "feat: integrate DailyBudget into translation pipeline

- config.yaml に daily_char_limit / char_usage_path を追加
- main.py でバジェット超過記事をスキップし翌日再翻訳を可能にする
- バジェット超過記事は英語のまま RSS に含める"
```

---

## 自己レビューメモ

- `budget_skipped` の初期化スコープ: `new_articles` ブロック外で宣言し、`all_translated` 構築時に参照 → スコープエラーなし
- `_MAX_DESCRIPTION_CHARS` を `src/translator.py` からインポート: 文字数カウントとバッチ翻訳で同一の切り詰め長を使うための一貫性確保
- `budget.consume()` は翻訳成功時のみ呼び出す（`results is not None` の中） → 失敗した場合はバジェットを消費しない
- `can_translate()` のチェックはテキスト全体（title + description[:500]）の合計文字数で行う → 仕様と一致
