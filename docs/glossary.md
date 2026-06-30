# ユビキタス言語定義

このプロジェクトで使用するドメイン用語・英日対応表・コード上の命名規則を定義します。

## ドメイン用語

| 用語 | 定義 |
|------|------|
| **フィード (Feed)** | RSSまたはAtom形式で配信される記事の配信元。`config.yaml`の`feeds`セクションで登録する |
| **記事 (Article)** | フィードから取得した個別のニュース記事。GUIDで一意に識別する |
| **翻訳済み記事 (TranslatedArticle)** | 記事に翻訳結果・要約を付加したデータ。キャッシュに保存される |
| **GUID** | 記事を一意に識別するID。多くの場合は記事URLと同一。キャッシュのキーとして使用する |
| **キャッシュ (Cache)** | 翻訳済み記事を`cache/translated.json`にGUIDをキーとして保存したもの。差分更新に使用する |
| **HTTPキャッシュ (HTTP Cache)** | フィードのETag/Last-Modifiedを`cache/http_cache.json`に保存したもの。不要なフィード取得を防ぐ |
| **差分更新** | キャッシュに存在しないGUIDの記事のみを翻訳・要約する処理 |
| **翻訳エンジン (Translator)** | タイトル・概要を機械翻訳するコンポーネント。Google Translate / OpenAI / DeepL / Claude |
| **要約エンジン (Summarizer)** | LLMを使って自然な日本語タイトルと3行要約を生成するコンポーネント。OpenAI / Claude |
| **自然な日本語タイトル (natural_title)** | 直訳でなく読みやすさを重視してLLMが生成した日本語タイトル |
| **要約 (summary)** | LLMが生成した3行程度の日本語要約 |
| **パイプライン (Pipeline)** | フィード取得→翻訳→要約→キャッシュ保存→RSS生成という一連の処理フロー |

## コンポーネント用語

| 用語 | 定義 |
|------|------|
| **Fetcher** | RSSフィードを取得して`Article`リストに変換するモジュール（`src/fetcher.py`） |
| **Translator** | 翻訳処理のProtocolインターフェース（`src/translator.py`） |
| **Summarizer** | 要約処理のProtocolインターフェース（`src/summarizer.py`） |
| **Generator** | `TranslatedArticle`リストからRSS XMLを生成するモジュール（`src/generator.py`） |
| **FeedConfig** | フィードのname・URLを持つ設定データクラス |

## 英語・日本語対応表

| 英語 | 日本語 | コード上の名前 |
|------|--------|--------------|
| Feed | フィード | `FeedConfig`, `feeds` |
| Article | 記事 | `Article` |
| Translated Article | 翻訳済み記事 | `TranslatedArticle` |
| GUID | GUID | `guid` |
| Title | タイトル | `title`, `translated_title`, `natural_title` |
| Description | 概要・説明 | `description`, `translated_description` |
| Summary | 要約 | `summary` |
| Source | 配信元 | `source` |
| Published | 公開日時 | `published` |
| Translator | 翻訳エンジン | `Translator`, `translator` |
| Summarizer | 要約エンジン | `Summarizer`, `summarizer` |
| Cache | キャッシュ | `cache`, `translated_cache`, `http_cache` |
| Engine | エンジン | `engine` |
| Retry | リトライ | `with_retry`, `max_attempts` |

## コード上の命名規則

### ファイル・モジュール
- モジュール名はスネークケース（`fetcher.py`, `translator.py`）
- 翻訳エンジンは `src/translators/<engine>.py`
- 要約エンジンは `src/summarizers/<engine>.py`
- テストファイルは `tests/test_<module>.py`

### クラス
- クラス名はパスカルケース（`Article`, `TranslatedArticle`, `GoogleTranslator`）
- Protocolクラスはインターフェース名（`Translator`, `Summarizer`）
- 具象実装クラスはエンジン名+役割（`GoogleTranslator`, `OpenAISummarizer`）

### 関数・メソッド
- 関数名はスネークケース（`fetch_feed`, `translate_articles`, `generate_rss`）
- ファクトリ関数は `get_<type>` （`get_translator`, `get_summarizer`）
- ローダー関数は `load_<target>` （`load_translated_cache`, `load_config`）
- セーバー関数は `save_<target>` （`save_translated_cache`, `save_http_cache`）

### 変数・引数
- 変数名はスネークケース（`translated_articles`, `http_cache`）
- 型変数は大文字1文字（`T`）
- `target_lang` は翻訳先言語コード（デフォルト: `"ja"`）

### 設定・定数
- 定数はアッパースネークケース（`DEFAULT_SUMMARIZER_PROMPT`）
- 設定キーはスネークケース（`max_items`, `http_cache_path`）
