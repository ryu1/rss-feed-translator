<p align="center">
  <img src="docs/images/logo.svg" alt="rss-feed-translator" width="420">
</p>
<p align="center">
    <em>海外ITニュースを自動翻訳・要約して、日本語RSSフィードとして配信するサーバーレスシステム。</em>
</p>
<p align="center">
  <a href="https://github.com/ryu1/rss-feed-translator/actions/workflows/update-rss.yml">
    <img src="https://github.com/ryu1/rss-feed-translator/actions/workflows/update-rss.yml/badge.svg" alt="Update RSS">
  </a>
  <a href="https://github.com/ryu1/rss-feed-translator/actions/workflows/test.yml">
    <img src="https://github.com/ryu1/rss-feed-translator/actions/workflows/test.yml/badge.svg" alt="Test">
  </a>
  <a href="https://github.com/ryu1/rss-feed-translator">
    <img src="https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://ryu1.github.io/rss-feed-translator/report.html">
    <img src="https://img.shields.io/badge/Review_Report-GitHub_Pages-22863A?logo=github&logoColor=white" alt="Report">
  </a>
</p>

---

**RSSフィード**: [Ars Technica](https://ryu1.github.io/rss-feed-translator/feed/ars-technica.xml) · [Hacker News](https://ryu1.github.io/rss-feed-translator/feed/hacker-news.xml) · [DEV Community](https://ryu1.github.io/rss-feed-translator/feed/dev-community.xml) · [InfoQ](https://ryu1.github.io/rss-feed-translator/feed/infoq.xml)

**翻訳・要約レポート**: [report.html](https://ryu1.github.io/rss-feed-translator/report.html)

---

英語の海外ITニュースを毎日自動で日本語に翻訳・要約し、Feedlyなどのフィードリーダーで購読できる形式で配信します。

主な特長:

- **自動翻訳**: Google Translate API でタイトルと説明文を日本語に翻訳
- **AI要約**: Claude Haiku（Amazon Bedrock）で自然な日本語タイトルと3行要約を生成
- **差分更新**: 翻訳済み記事はキャッシュし、新着記事のみを処理
- **コスト管理**: 1日あたりの翻訳文字数に上限を設定可能
- **サーバーレス**: GitHub Actions + GitHub Pages のみで運用。追加インフラ不要
- **1日2回自動更新**: JST 9:00・12:00 に自動実行（手動実行も可）

## ドキュメント

- [設計ドキュメント](docs/superpowers/specs/2026-06-29-rss-feed-translator-design.md) — アーキテクチャ・セットアップ・設定・開発コマンド
- [実装計画](docs/superpowers/plans/2026-06-29-rss-feed-translator.md) — 初回実装のタスクリスト
- [用語定義](docs/glossary.md) — ドメイン用語・命名規則
