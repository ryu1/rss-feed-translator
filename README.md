# rss-feed-translator

海外の英語RSSフィードを日本語に翻訳し、GitHub Pages で配信するシステムです。

## 機能

- 複数の RSS フィード（RSS 2.0 / Atom）を取得
- タイトル・説明文を AI で日本語翻訳
- LLM による自然な日本語タイトルと3行要約の生成
- 翻訳結果をキャッシュして差分のみ処理
- GitHub Actions で30分ごとに自動更新
- GitHub Pages で `rss.xml` を配信

## RSSフィード

```
https://ryu1.github.io/rss-feed-translator/feed/rss.xml
```

## セットアップ

### 必要なもの

- Python 3.12.10
- [uv](https://docs.astral.sh/uv/)

### インストール

```bash
git clone https://github.com/ryu1/rss-feed-translator.git
cd rss-feed-translator
uv sync --all-extras
```

### 設定

`config.yaml` を編集してフィードや翻訳エンジンを設定します。

```yaml
feeds:
  - name: Ars Technica
    url: https://feeds.arstechnica.com/arstechnica/index
  - name: Hacker News
    url: https://hnrss.org/frontpage

translator:
  engine: openai  # google | openai | deepl | claude

summarizer:
  enabled: true
  engine: openai  # openai | claude
  model: gpt-4o-mini
```

### 環境変数

使用するエンジンに応じて API キーを設定します。

| 変数名 | 用途 |
|--------|------|
| `OPENAI_API_KEY` | 翻訳・要約（OpenAI） |
| `ANTHROPIC_API_KEY` | 翻訳・要約（Claude） |
| `GOOGLE_API_KEY` | 翻訳（Google Cloud Translation） |
| `DEEPL_API_KEY` | 翻訳（DeepL） |

### ローカル実行

```bash
export OPENAI_API_KEY=your_key
uv run python main.py
```

## GitHub Actions の設定

1. リポジトリの **Settings → Secrets and variables → Actions** で API キーを登録
2. **Settings → Pages** でソースを `main` ブランチの `/docs` フォルダに設定
3. Actions タブから `Update RSS` ワークフローを手動実行して動作確認

## 開発

```bash
# テスト
uv run pytest tests/ -v

# リント
uv run ruff check src/ tests/

# 型チェック
uv run mypy src/
```

## 翻訳エンジン

| エンジン | 設定値 | API キー |
|---------|--------|---------|
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Claude | `claude` | `ANTHROPIC_API_KEY` |
| Google Cloud Translation | `google` | `GOOGLE_API_KEY` |
| DeepL | `deepl` | `DEEPL_API_KEY` |
