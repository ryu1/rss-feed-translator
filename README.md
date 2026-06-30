# rss-feed-translator

海外の英語RSSフィードを日本語に翻訳し、GitHub Pages で配信するシステムです。

## RSSフィード

```
https://ryu1.github.io/rss-feed-translator/feed/rss.xml
```

## セットアップ

**必要なもの:** Python 3.12.10、[uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/ryu1/rss-feed-translator.git
cd rss-feed-translator
uv sync --all-extras
```

## 設定

`config.yaml` でフィードと翻訳エンジンを設定します。APIキーは環境変数で渡します。

```yaml
feeds:
  - name: Ars Technica
    url: https://feeds.arstechnica.com/arstechnica/index

translator:
  engine: openai  # google | openai | deepl | claude

summarizer:
  enabled: true
  engine: openai
  model: gpt-4o-mini
```

```bash
export OPENAI_API_KEY=your_key
uv run python main.py
```

## GitHub Actions の設定

1. **Settings → Secrets** で使用するエンジンの API キーを登録
2. **Settings → Pages** でソースを `main` ブランチの `/docs` フォルダに設定
3. Actions タブから `Update RSS` を手動実行して動作確認

## 開発

```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run mypy src/
```

## ドキュメント

- [設計ドキュメント](docs/superpowers/specs/2026-06-29-rss-feed-translator-design.md) — アーキテクチャ・データモデル・コンポーネント設計
- [実装計画](docs/superpowers/plans/2026-06-29-rss-feed-translator.md) — 初回実装のタスクリスト
- [用語定義](docs/glossary.md) — ドメイン用語・命名規則
