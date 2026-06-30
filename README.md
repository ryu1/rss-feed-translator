# rss-feed-translator

[![Update RSS](https://github.com/ryu1/rss-feed-translator/actions/workflows/update-rss.yml/badge.svg)](https://github.com/ryu1/rss-feed-translator/actions/workflows/update-rss.yml)
[![Test](https://github.com/ryu1/rss-feed-translator/actions/workflows/test.yml/badge.svg)](https://github.com/ryu1/rss-feed-translator/actions/workflows/test.yml)

海外の英語RSSフィードを日本語に翻訳し、GitHub Pages で配信するシステムです。

## RSSフィード

フィードごとに個別のXMLファイルを生成・公開しています。

| フィード | URL |
|---|---|
| Ars Technica | `https://ryu1.github.io/rss-feed-translator/feed/ars-technica.xml` |
| Hacker News | `https://ryu1.github.io/rss-feed-translator/feed/hacker-news.xml` |
| DEV Community | `https://ryu1.github.io/rss-feed-translator/feed/dev-community.xml` |

## ドキュメント

- [設計ドキュメント](docs/superpowers/specs/2026-06-29-rss-feed-translator-design.md) — アーキテクチャ・セットアップ・設定・開発コマンド
- [実装計画](docs/superpowers/plans/2026-06-29-rss-feed-translator.md) — 初回実装のタスクリスト
- [用語定義](docs/glossary.md) — ドメイン用語・命名規則
