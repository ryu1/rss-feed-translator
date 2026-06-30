# RSS Feed Translator — 設計ドキュメント

作成日: 2026-06-29

---

## 目次

- [概要](#概要)
- [プロダクト定義](#プロダクト定義)

**アーキテクチャ・設計**
- [アーキテクチャ](#アーキテクチャ)
- [リポジトリ構造](#リポジトリ構造)
- [設定ファイル（config.yaml）](#設定ファイルconfigyaml)
- [データモデル（src/models.py）](#データモデルsrcmodelspy)

**コンポーネント**
- [RSS取得（src/fetcher.py）](#rss取得srcfetcherpy)
- [翻訳エンジン（src/translator.py）](#翻訳エンジンsrctranslatorpysrctranslatorspy)
- [LLM要約処理（src/summarizer.py）](#llm要約処理srcsumarizerpysrcsumarizerspy)
- [RSS生成（src/generator.py）](#rss生成srcgeneratorpy)
- [キャッシュ（src/cache.py）](#キャッシュsrccachepy)
- [カスタム例外（src/exceptions.py）](#カスタム例外srcexceptionspy)

**運用・インフラ**
- [エラー処理](#エラー処理)
- [ログ](#ログ)
- [GitHub Actionsワークフロー](#github-actionsワークフロー)
- [ブランチ保護（Rulesets）](#ブランチ保護rulesets)
- [GitHub Pages設定](#github-pages設定)

**開発**
- [依存関係（pyproject.toml）](#依存関係pyprojecttoml)
- [開発環境セットアップ](#開発環境セットアップ)
- [コーディング規約](#コーディング規約)
- [テスト方針](#テスト方針)

- [将来的な拡張への考慮](#将来的な拡張への考慮)

---

## 概要

海外RSSフィードを定期的に取得し、記事タイトルおよび概要を日本語に翻訳した新しいRSSフィードを生成・公開するシステム。GitHub Actions + GitHub Pagesで完全サーバーレスに運用する。

---

## プロダクト定義

### プロダクトビジョン

英語の海外ITニュースを日本語で手間なく読めるようにする個人向け自動翻訳RSSフィード。Feedlyに登録するだけで、毎日最新の海外IT情報が日本語で届く状態を実現する。

### ターゲットユーザー・課題

**ターゲットユーザー**: 海外ITニュースを追いたいが英語が障壁になっている個人（自分自身）

**解決する課題**:
- 英語が苦手なため、英語のまま読もうとすると途中で挫折し、海外ニュースから遠ざかってしまう
- Google翻訳などを都度手動で使うのが手間で、継続した情報収集の習慣が続かない

### 機能要件

- 指定した海外RSSフィードを定期的に取得する
- 記事タイトルおよび概要を日本語に翻訳する
- 翻訳済み記事はキャッシュし、再翻訳しない
- LLMで自然な日本語タイトルと3行要約を生成できる（オプション）
- フィードごとに個別のRSSファイルを生成し、GitHub Pagesで公開する
- タイトルに `[翻訳]` プレフィックスを付与し、翻訳フィードと識別できる

### 非機能要件

- サーバー不要（GitHub Actions + GitHub Pagesのみで運用）
- 1日2回自動更新（JST 9:00・12:00）
- 手動実行で任意のタイミングでも更新可能
- 翻訳コストを最小化する（キャッシュ・バッチ翻訳・チャンク分割）

### ユーザーストーリー・受け入れ条件

**ユーザーストーリー**: Feedlyを開いたとき、海外ITニュースが日本語で他のフィードと並んで表示されている。`[翻訳]` プレフィックスでひと目で翻訳フィードとわかり、英語の障壁なく毎日読み続けられる。

**受け入れ条件**:
- FeedlyでRSSフィードURLを登録でき、記事タイトルが日本語で表示される
- タイトルに `[翻訳]` プレフィックスが付いている
- 1日2回自動更新され、新着記事が翻訳されている
- サーバーを別途用意しなくても動作する
- 英語のまま読む必要がなく、継続して情報収集できる

---

## アーキテクチャ・設計

### アーキテクチャ

#### システム全体構成

```mermaid
graph TD
    subgraph "GitHub Actions（JST 9:00・12:00 / 1日2回）"
        MAIN["main.py"]
    end

    subgraph "外部RSSフィード"
        FEED1["Ars Technica"]
        FEED2["Hacker News"]
        FEED3["DEV Community"]
    end

    subgraph "翻訳・要約API"
        TRANS["翻訳エンジン\nOpenAI / Google / DeepL / Claude"]
        SUMM["要約エンジン\nOpenAI / Claude"]
    end

    subgraph "リポジトリ"
        CACHE["cache/translated.json\nhttp_cache.json"]
        RSS["docs/feed/ars-technica.xml\ndocs/feed/hacker-news.xml\ndocs/feed/dev-community.xml"]
    end

    subgraph "GitHub Pages"
        PUB["https://ryu1.github.io/\nrss-feed-translator/feed/<feed>.xml"]
    end

    FEED1 -->|RSS取得| MAIN
    FEED2 -->|RSS取得| MAIN
    FEED3 -->|RSS取得| MAIN
    MAIN -->|翻訳リクエスト| TRANS
    MAIN -->|要約リクエスト| SUMM
    MAIN -->|読み書き| CACHE
    MAIN -->|生成| RSS
    RSS -->|自動公開| PUB
```

#### パイプライン（データフロー）

単一の`main.py`エントリポイントから5つのモジュールをシーケンシャルに呼び出す。

```mermaid
flowchart LR
    CONFIG["config.yaml"]
    FETCH["fetch_feeds()\nfetcher.py"]
    CACHE_R["キャッシュ参照\ncache.py"]
    TRANS["translate_articles()\ntranslator.py"]
    SUMM["process_articles()\nsummarizer.py\n※optonal"]
    CACHE_W["save_cache()\ncache.py"]
    GEN["generate_rss()\ngenerator.py"]

    CONFIG --> FETCH
    FETCH -->|"List[Article]"| CACHE_R
    CACHE_R -->|"新着記事のみ"| TRANS
    TRANS -->|"List[TranslatedArticle]"| SUMM
    SUMM -->|"List[TranslatedArticle]"| CACHE_W
    CACHE_W -->|"全キャッシュ"| GEN
```

**翻訳とLLM処理の2段階設計:**

- **翻訳**（`Translator`）: タイトル・概要の機械翻訳。高速・低コスト
- **LLM処理**（`Summarizer`）: 自然な日本語タイトル + 3行要約。翻訳後にオプションで実行

`config.yaml`の`summarizer.enabled`で切り替え可能。

### リポジトリ構造

```
rss-feed-translator/
├── config.yaml                      # フィード・翻訳エンジン設定
├── main.py                          # エントリポイント
├── src/
│   ├── fetcher.py                   # RSS取得（ETag/Last-Modified対応）
│   ├── translator.py                # Translatorプロトコル定義 + エンジン選択
│   ├── translators/
│   │   ├── google.py                # Google Translate実装
│   │   ├── openai.py                # OpenAI翻訳実装
│   │   ├── claude.py                # Claude翻訳実装（Anthropic / Bedrock）
│   │   └── deepl.py                 # DeepL実装
│   ├── summarizer.py                # Summarizerプロトコル定義 + エンジン選択
│   ├── summarizers/
│   │   ├── openai.py                # OpenAI（GPT-4o等）実装
│   │   └── claude.py                # Claude実装（Anthropic / Bedrock）
│   ├── generator.py                 # RSS XML生成
│   ├── cache.py                     # 翻訳キャッシュ管理
│   ├── models.py                    # データクラス定義
│   └── exceptions.py                # カスタム例外クラス
├── tests/
│   ├── conftest.py                  # pytest共通フィクスチャ
│   ├── test_fetcher.py
│   ├── test_translator.py
│   ├── test_summarizer.py
│   ├── test_cache.py
│   ├── test_generator.py
│   ├── test_models.py
│   └── test_pipeline.py
├── cache/
│   ├── translated.json              # 翻訳済み記事キャッシュ（gitコミット対象）
│   └── http_cache.json              # ETag/Last-Modifiedキャッシュ（gitコミット対象）
├── docs/
│   └── feed/
│       ├── ars-technica.xml         # フィード別RSS（GitHub Pages公開）
│       ├── hacker-news.xml
│       └── dev-community.xml
├── .github/
│   ├── workflows/
│   │   ├── update-rss.yml           # 1日2回cron（JST 9:00・12:00）+ workflow_dispatch
│   │   ├── dependabot-auto-merge.yml # Dependabot patch自動マージ
│   │   └── test.yml                 # プッシュ時のテスト実行
│   ├── rulesets/
│   │   └── main-protection.json     # ブランチ保護Ruleset（インポート用）
│   └── dependabot.yml               # Dependabot設定
├── .pre-commit-config.yaml          # ruff lint + ruff-format
├── pyproject.toml                   # 依存関係・リンター設定
└── uv.lock                          # 依存関係ロックファイル
```

### 設定ファイル（config.yaml）

```yaml
feeds:
  - name: Ars Technica
    url: https://feeds.arstechnica.com/arstechnica/index
    output_path: docs/feed/ars-technica.xml   # per-feed 出力ファイルパス
    link_url: https://arstechnica.com         # RSS <channel><link>
  - name: Hacker News
    url: https://hnrss.org/frontpage
    output_path: docs/feed/hacker-news.xml
    link_url: https://news.ycombinator.com
  - name: DEV Community
    url: https://dev.to/feed
    output_path: docs/feed/dev-community.xml
    link_url: https://dev.to

translator:
  engine: openai   # google | openai | deepl | claude
  # provider: anthropic  # anthropic (default) | bedrock

summarizer:
  enabled: true                  # falseにすると翻訳のみ
  engine: openai                 # openai | claude
  model: gpt-4o-mini             # 使用モデル（コスト最適化）
  # provider: anthropic          # anthropic (default) | bedrock
  # prompt: |                    # 省略時は DEFAULT_SUMMARIZER_PROMPT を使用

output:
  max_items: 200   # フィードごとのRSSに含める最大記事数

cache:
  path: cache/translated.json
  http_cache_path: cache/http_cache.json
```

APIキーはGitHub Secretsから環境変数として注入する。設定ファイルにはハードコードしない。

### データモデル（src/models.py）

全クラスに型ヒントを付与する。`dataclass`を使用してイミュータブルなデータ構造を定義する。

```mermaid
classDiagram
    class FeedConfig {
        +str name
        +str url
        +str|None output_path
        +str link_url
    }
    class Article {
        +str guid
        +str title
        +str description
        +str link
        +datetime published
        +str source
    }
    class TranslatedArticle {
        +str guid
        +str original_title
        +str original_description
        +str|None translated_title
        +str|None translated_description
        +str|None natural_title
        +str|None summary
        +str link
        +datetime published
        +str source
        +datetime translated_at
    }

    FeedConfig --> Article : fetcher.py が生成
    Article --> TranslatedArticle : translator/summarizer が変換
```

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class FeedConfig:
    name: str
    url: str
    output_path: str | None = None   # per-feed 出力ファイルパス
    link_url: str = ""               # RSS <channel><link>

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
    translated_title: str | None        # 翻訳失敗時はNone
    translated_description: str | None
    natural_title: str | None           # LLM生成の自然な日本語タイトル（summarizer無効時はNone）
    summary: str | None                 # LLM生成の3行要約（summarizer無効時はNone）
    link: str
    published: datetime
    source: str
    translated_at: datetime
```

RSS生成時は`natural_title`が存在すれば優先して使用し、なければ`translated_title`にフォールバックする。`summary`が存在すれば`<description>`に使用する。

---

## コンポーネント

### RSS取得（src/fetcher.py）

```mermaid
sequenceDiagram
    participant M as main.py
    participant F as fetcher.py
    participant R as RSS Server
    participant C as http_cache.json

    M->>F: fetch_all_feeds(feeds, http_cache)
    loop 各フィード
        F->>C: ETag / Last-Modified を読み込み
        F->>R: GET feed (If-None-Match / If-Modified-Since)
        alt 304 Not Modified
            R-->>F: 304
            F-->>M: [] (スキップ)
        else 200 OK
            R-->>F: フィードデータ
            F->>C: ETag / Last-Modified を保存
            F-->>M: List[Article]
        end
    end
```

- `feedparser`でRSS 2.0およびAtomを解析
- `requests`でHTTPリクエスト。ETag / Last-Modifiedをリクエストヘッダに付与し、304 Not Modifiedを活用
- フィードごとに独立してtry/catchし、取得失敗しても他フィードの処理を継続
- 新着記事の判定はキャッシュのGUID一覧との差分で行う

### 翻訳エンジン（src/translator.py / src/translators/）

```mermaid
classDiagram
    class Translator {
        <<Protocol>>
        +translate(texts: list[str], target_lang: str) list[str]
    }
    class GoogleTranslator {
        +translate(texts, target_lang) list[str]
    }
    class OpenAITranslator {
        +translate(texts, target_lang) list[str]
    }
    class DeepLTranslator {
        +translate(texts, target_lang) list[str]
    }
    class ClaudeTranslator {
        +translate(texts, target_lang) list[str]
    }

    Translator <|.. GoogleTranslator : implements
    Translator <|.. OpenAITranslator : implements
    Translator <|.. DeepLTranslator : implements
    Translator <|.. ClaudeTranslator : implements
```

#### Protocolインターフェース

```python
from typing import Protocol

class Translator(Protocol):
    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        ...
```

構造的サブタイピングにより継承不要。`translate()`メソッドを持つクラスであれば自動的に適合する。

#### エンジン一覧

| エンジン | キー | 認証環境変数 |
|---|---|---|
| Google Translate | `google` | `GOOGLE_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| DeepL | `deepl` | `DEEPL_API_KEY` |
| Claude（Anthropic直接） | `claude` | `ANTHROPIC_API_KEY` |
| Claude（Amazon Bedrock） | `claude` + `provider: bedrock` | `AWS_BEARER_TOKEN_BEDROCK` |

`config.yaml`の`translator.engine`で切り替え。`provider`を`bedrock`にするとAmazon Bedrock経由でClaudeを使用する（IAM認証不使用、`AWS_BEARER_TOKEN_BEDROCK`のBearer Token方式のみ）。

#### 翻訳対象

- `title`（記事タイトル）
- `description`（記事概要）
- 本文（full text）は対象外

#### バッチ翻訳

1記事ずつではなく、新着記事の title・description をまとめてAPIに送信しAPI呼び出し回数を最小化する。description は翻訳前に500文字に切り詰める（DEV Communityなど記事本文が含まれるフィードの対策）。一度に送るテキスト数が多いとレスポンスがトークン上限で切れるため、10件ずつのチャンクに分割して送信する。

#### リトライ（指数バックオフ）

```mermaid
sequenceDiagram
    participant T as translate_articles()
    participant R as with_retry()
    participant A as 翻訳API

    T->>R: with_retry(fn, max_attempts=3)
    R->>A: attempt 1
    A-->>R: TranslationError
    Note over R: sleep 1s
    R->>A: attempt 2
    A-->>R: TranslationError
    Note over R: sleep 2s
    R->>A: attempt 3
    alt 成功
        A-->>R: list[str]
        R-->>T: list[str]
    else 失敗
        A-->>R: TranslationError
        R-->>T: TranslationSkippedError（スキップ）
    end
```

### LLM要約処理（src/summarizer.py / src/summarizers/）

```mermaid
classDiagram
    class Summarizer {
        <<Protocol>>
        +summarize(article: Article) tuple[str, str]
    }
    class OpenAISummarizer {
        +summarize(article) tuple[str, str]
    }
    class ClaudeSummarizer {
        +summarize(article) tuple[str, str]
    }

    Summarizer <|.. OpenAISummarizer : implements
    Summarizer <|.. ClaudeSummarizer : implements
```

#### Protocolインターフェース

```python
from typing import Protocol
from src.models import Article

class Summarizer(Protocol):
    def summarize(self, article: Article) -> tuple[str, str]:
        """(natural_title, summary) を返す"""
        ...
```

翻訳エンジンと同様にProtocolで抽象化。`config.yaml`の`summarizer.enabled: false`で無効化でき、翻訳のみの構成にも対応する。

#### エンジン

- **OpenAI**（`gpt-4o-mini`推奨）: コスト低、応答速度良好
- **Claude**（`claude-haiku-4-5-20251001`推奨）: 日本語品質が高い

#### プロンプト設計

記事の`title`・`description`・`source`を入力とし、構造化された出力（JSONモード）を使って`natural_title`と`summary`を確実に取得する。

期待するJSON出力フォーマット:
```json
{
  "natural_title": "自然な日本語タイトル",
  "summary": "1行目の要約。\n2行目の要約。\n3行目の要約。"
}
```

#### コスト考慮

`summarizer`はLLM呼び出しのためコストが発生する。キャッシュに`natural_title`と`summary`を保存し、再処理を防ぐ。設定で`enabled: false`にすれば翻訳APIのみで動作する低コスト構成にいつでも戻せる。

### RSS生成（src/generator.py）

#### タイトル・説明文のフォールバック

```mermaid
flowchart LR
    subgraph title ["タイトル選択"]
        NT{"natural_title\nあり?"}
        TT{"translated_title\nあり?"}
        OT["original_title\n（元記事タイトル）"]
        NT -->|Yes| NT_OUT["natural_title を使用"]
        NT -->|No| TT
        TT -->|Yes| TT_OUT["translated_title を使用"]
        TT -->|No| OT
    end

    subgraph desc ["説明文選択"]
        SM{"summary\nあり?"}
        TD{"translated_description\nあり?"}
        OD["original_description\n（元記事概要）"]
        SM -->|Yes| SM_OUT["summary を使用"]
        SM -->|No| TD
        TD -->|Yes| TD_OUT["translated_description を使用"]
        TD -->|No| OD
    end
```

- `defusedxml`を使いXXE/Billion Laughs攻撃を防ぐ。生成には`xml.etree.ElementTree`、解析には`defusedxml.ElementTree`を使用
- キャッシュの全件を`pubDate`降順でソートし、`max_items`件まで出力
- **フィード別出力**: `FeedConfig.output_path` に指定されたパスへフィードごとに個別ファイルを生成（`docs/feed/ars-technica.xml` など）
- `<channel><link>` は `FeedConfig.link_url` から設定（空文字列の場合は空で出力）

#### タイトルプレフィックス

全記事のタイトル先頭に `[翻訳]` を付与する。翻訳成功・失敗を問わず常に付与し、Feedly などのリーダーでこのフィードが翻訳フィードであることを一目で識別できるようにする。

#### itemの構成

```xml
<item>
  <title>[翻訳] AI分野の突破口</title>
  <description>研究者たちは...</description>
  <link>https://example.com/article-1</link>
  <pubDate>Mon, 29 Jun 2026 10:00:00 +0000</pubDate>
  <source>Ars Technica</source>
  <guid isPermaLink="false">https://example.com/article-1</guid>
  <original:title>AI Breakthrough</original:title>
</item>
```

GUIDは元記事のGUIDをそのまま保持する。

### キャッシュ（src/cache.py）

#### 差分更新フロー

```mermaid
flowchart TD
    FETCH["fetch_all_feeds()\n全記事取得"]
    LOAD["load_translated_cache()\nキャッシュ読み込み"]
    DIFF{"GUID が\nキャッシュに存在?"}
    SKIP["スキップ\n（翻訳済み）"]
    TRANS["translate_articles()\n翻訳・要約"]
    SAVE["save_translated_cache()\nキャッシュ保存"]

    FETCH --> LOAD
    LOAD --> DIFF
    DIFF -->|Yes| SKIP
    DIFF -->|No| TRANS
    TRANS --> SAVE
    SKIP --> SAVE
```

#### translated.json

GUIDをキーとしたJSONオブジェクト。差分更新はGUIDの存在確認のみでO(1)。

**キャッシュ上限（プルーニング）:** `save_translated_cache()` 呼び出し時にエントリ数が 10,000 を超えると、`published` 降順でソートして上位 10,000 件に自動プルーニングされる。

```json
{
  "https://example.com/article-1": {
    "original_title": "AI Breakthrough",
    "original_description": "Researchers found...",
    "translated_title": "AI分野の突破口",
    "translated_description": "研究者たちは...",
    "natural_title": "AI研究に新たな突破口、業界に波紋",
    "summary": "研究者チームが新たなAIアーキテクチャを発表した。\n従来手法の10倍の効率を達成し、エネルギー消費も大幅に削減。\n商用化に向けた実証実験が2026年内に開始される予定。",
    "source": "Ars Technica",
    "published": "2026-06-29T10:00:00Z",
    "link": "https://example.com/article-1",
    "translated_at": "2026-06-29T10:05:00Z"
  }
}
```

`natural_title`・`summary`はsummarizer無効時は`null`として保存される。

翻訳失敗でスキップされた記事も`translated_title: null`でキャッシュに保存し、無限リトライを防止する。再翻訳が必要な場合はキャッシュエントリを手動削除する。

#### http_cache.json

フィードURLをキーとして`ETag`と`Last-Modified`を保存。

```json
{
  "https://feeds.arstechnica.com/arstechnica/index": {
    "etag": "\"abc123\"",
    "last_modified": "Mon, 29 Jun 2026 10:00:00 GMT"
  }
}
```

### カスタム例外（src/exceptions.py）

エラー種別を明示的に分類し、呼び出し元でのハンドリングを容易にする。

```mermaid
classDiagram
    class Exception
    class FeedFetchError
    class TranslationError
    class TranslationSkippedError
    class SummarizationError
    class SummarizationSkippedError

    Exception <|-- FeedFetchError
    Exception <|-- TranslationError
    Exception <|-- SummarizationError
    TranslationError <|-- TranslationSkippedError
    SummarizationError <|-- SummarizationSkippedError
```

```python
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

---

## 運用・インフラ

### エラー処理

| 状況 | 動作 |
|---|---|
| RSS取得失敗 | `WARNING`ログを出力して次のフィードへ継続 |
| 翻訳API失敗 | 指数バックオフで最大3回リトライ（1秒→2秒→4秒） |
| 3回失敗した記事（翻訳） | `ERROR`ログを出力してスキップ。`translated_title: null`でキャッシュ保存 |
| LLM要約API失敗 | 指数バックオフで最大3回リトライ |
| 3回失敗した記事（要約） | `ERROR`ログを出力してスキップ。`natural_title: null`でキャッシュ保存。翻訳結果はそのまま使用 |
| GitHub Actions全体 | スキップがあっても`exit 0`で正常終了 |

各フィード・各記事単位で例外をキャッチし、システム全体が停止しない設計とする。

### ログ

Pythonの標準`logging`モジュールを使用。`StreamHandler`でGitHub Actionsのコンソールに出力。

```
[INFO]  Starting RSS feed translator
[INFO]  Fetching 5 feeds...
[INFO]  Feed: Ars Technica — 10 articles fetched (3 new)
[ERROR] Feed: Hacker News — fetch failed: Connection timeout (skipped)
[INFO]  Translating 12 articles (8 cache hits, 4 new)...
[INFO]  Translated: 4 articles (2 retried, 0 skipped)
[INFO]  Summarizing 4 articles with LLM (summarizer=openai/gpt-4o-mini)...
[INFO]  Summarized: 4 articles (0 skipped)
[INFO]  RSS generated: docs/rss.xml (112 articles total)
[INFO]  Done in 31.2s | fetched=20 new=12 translated=4 summarized=4 errors=1
```

最終行のサマリー行でGitHub Actionsのログから一目で状況を把握できる。

### GitHub Actionsワークフロー

```mermaid
graph LR
    subgraph "test.yml"
        PUSH["push / pull_request"] --> TEST["pytest\nruff\nmypy"]
    end

    subgraph "update-rss.yml"
        CRON["schedule\nJST 9:00・12:00\n1日2回"] --> RUN["main.py 実行"]
        DISPATCH["workflow_dispatch\n手動実行"] --> RUN
        RUN --> COMMIT["cache/ + docs/feed/\nコミット＆プッシュ"]
        COMMIT --> PAGES["GitHub Pages\n自動デプロイ"]
    end

    subgraph "dependabot-auto-merge.yml"
        DEP["Dependabot PR"] --> CHECK["patch update?"]
        CHECK -->|Yes| MERGE["自動マージ"]
        CHECK -->|No| MANUAL["手動マージ"]
    end
```

#### update-rss.yml（.github/workflows/update-rss.yml）

- **スケジュール**: JST 9:00 と 12:00 の1日2回実行（UTC 0:00 と 3:00）
- **手動実行**: `workflow_dispatch` で任意のタイミングで実行可能
- **コミット対象**: `cache/`（翻訳キャッシュ）と `docs/feed/`（フィード別 RSS ファイル）
- **新着なし**: 差分がない場合はコミットをスキップ

**必要な GitHub Secrets:**

| Secret 名 | 用途 |
|---|---|
| `OPENAI_API_KEY` | OpenAI 翻訳・要約エンジン |
| `ANTHROPIC_API_KEY` | Claude 翻訳・要約エンジン（直接 API） |
| `AWS_BEARER_TOKEN_BEDROCK` | Claude 翻訳・要約エンジン（Bedrock 経由） |
| `AWS_DEFAULT_REGION` | Bedrock リージョン |
| `GOOGLE_API_KEY` | Google 翻訳エンジン |
| `DEEPL_API_KEY` | DeepL 翻訳エンジン |

#### test.yml（.github/workflows/test.yml）

- **トリガー**: push / pull_request
- **ステップ**: `pytest` → `ruff check` → `mypy`

#### dependabot-auto-merge.yml（.github/workflows/dependabot-auto-merge.yml）

- Dependabot の PR を自動検出
- **patch** アップデートのみ自動マージ（squash）
- **minor / major** は PR を作成するが手動マージが必要

#### dependabot.yml（.github/dependabot.yml）

- `pip`（Python パッケージ）と `github-actions` を毎週チェック
- 古いバージョンの依存があれば自動で PR を作成

### ブランチ保護（Rulesets）

`main` ブランチに以下のルールを適用（`.github/rulesets/main-protection.json`）。

| ルール | 内容 |
|---|---|
| `deletion` | `main` ブランチの削除を禁止 |
| `non_fast_forward` | force push を禁止 |
| `restrict_pushes` | `ryu1` 以外の直接 push を禁止 |

> **注意:** `pull_request` および `required_status_checks` ルールは適用していない。`github-actions[bot]` による RSS 更新の直接 push（`update-rss.yml`）は PR なしで行われるため、これらのルールを有効にするとワークフローがブロックされる。

JSON ファイルは `.github/rulesets/main-protection.json` に保存されており、GitHub の Import Ruleset 機能でインポートできる（インポート後 `bypass_actors` や `ryu1` の追加は GUI で行う）。

### GitHub Pages設定

リポジトリの Settings → Pages → Source を `docs/` フォルダに設定することで、以下の URL で RSS が公開される。

```
https://ryu1.github.io/rss-feed-translator/feed/ars-technica.xml
https://ryu1.github.io/rss-feed-translator/feed/hacker-news.xml
https://ryu1.github.io/rss-feed-translator/feed/dev-community.xml
```

---

## 開発

### 依存関係（pyproject.toml）

```toml
[project]
name = "rss-feed-translator"
requires-python = ">=3.12"
dependencies = [
    "feedparser",
    "requests",
    "pyyaml",
    "google-cloud-translate",
    "openai",
    "deepl",
    "anthropic",
    "defusedxml",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "responses",   # HTTPモック
    "mypy",
    "ruff",
    "pre-commit",
]

[tool.ruff]
line-length = 88

[tool.mypy]
strict = true
```

`uv.lock`をコミットすることでローカルとGitHub Actionsで完全に同一の依存関係を再現する。

### 開発環境セットアップ

```bash
# 依存関係インストール（dev含む）
uv sync --all-extras

# pre-commit フックをインストール（初回のみ）
uv run pre-commit install
```

インストール後は `git commit` のたびに lint・フォーマットが自動実行される。

#### 開発コマンド

| コマンド | 目的 |
|---------|------|
| `uv run pytest tests/ -v` | テスト実行 |
| `uv run ruff check src/ tests/` | lint チェック |
| `uv run ruff format src/ tests/` | コード整形 |
| `uv run mypy src/` | 型チェック |
| `uv run pre-commit run --all-files` | 全ファイルに pre-commit を手動実行 |
| `uv run python main.py` | パイプライン手動実行 |

### コーディング規約

- **型ヒント**: 全関数のパラメータと戻り値に型ヒントを付与する（`from __future__ import annotations`を活用）
- **例外処理**: 例外を握り潰さない。`except Exception`は最外層のみ。内部では`FeedFetchError`・`TranslationError`等のカスタム例外を使う
- **ログ**: 各モジュールは`logging.getLogger(__name__)`でロガーを取得し、適切なレベルで出力する
- **リンター**: `ruff`でコードスタイルを統一（`uv run ruff check src/ tests/`）
- **フォーマッター**: `ruff format`でコードを自動整形（`uv run ruff format src/ tests/`）
- **型チェック**: `mypy`またはpyrightで静的解析（`uv run mypy src/`）
- **pre-commit**: コミット前に `ruff --fix` と `ruff-format` が自動実行される。初回セットアップ時に `uv run pre-commit install` を実行すること

### テスト方針

- `tests/`配下にモジュール対応のテストファイルを配置し、`pytest`で実行
- 翻訳エンジンはProtocolを活用したモック実装でテスト（実APIを呼ばない）
- フィード取得は`responses`ライブラリでHTTPをモック
- `conftest.py`に共通フィクスチャ（サンプルフィード、モック翻訳器等）を定義
- 各テストは`Arrange / Act / Assert`の構造で記述し、1テスト1アサートを原則とする

#### テスト用GitHub Actionsワークフロー（.github/workflows/test.yml）

```yaml
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v7
      - run: uv sync --all-extras
      - run: uv run pytest tests/ -v
      - run: uv run ruff check src/ tests/
      - run: uv run mypy src/
```

---

## 将来的な拡張への考慮

以下の機能を追加しやすいよう、各モジュールを明確に分離した設計とする。

- AIによる要約・リライト → `summarizer.py`の`Summarizer`Protocolで既に設計済み（設定で有効化）
- Slack/Discord通知 → `main.py`にパイプラインステップとして追加
- Web管理画面 → `cache/translated.json`をデータソースとして利用
- 全文翻訳 → `Article`モデルに`full_text`フィールドを追加
