# rss-feed-translator

[![Update RSS](https://github.com/ryu1/rss-feed-translator/actions/workflows/update-rss.yml/badge.svg)](https://github.com/ryu1/rss-feed-translator/actions/workflows/update-rss.yml)
[![Test](https://github.com/ryu1/rss-feed-translator/actions/workflows/test.yml/badge.svg)](https://github.com/ryu1/rss-feed-translator/actions/workflows/test.yml)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-deployed-22863A?logo=github&logoColor=white)
![Google Translate](https://img.shields.io/badge/Translated_by-Google_Translate-4285F4?logo=googletranslate&logoColor=white)
![Claude](https://img.shields.io/badge/Summarized_by-Claude_Haiku-D97706?logo=anthropic&logoColor=white)

海外の英語RSSフィードを日本語に翻訳し、GitHub Pages で配信するシステムです。

## RSSフィード

フィードごとに個別のXMLファイルを生成・公開しています。

| フィード | URL |
|---|---|
| Ars Technica | `https://ryu1.github.io/rss-feed-translator/feed/ars-technica.xml` |
| Hacker News | `https://ryu1.github.io/rss-feed-translator/feed/hacker-news.xml` |
| DEV Community | `https://ryu1.github.io/rss-feed-translator/feed/dev-community.xml` |
| InfoQ | `https://ryu1.github.io/rss-feed-translator/feed/infoq.xml` |

## レビューレポート

翻訳・要約の精度を確認できます: [report.html](https://ryu1.github.io/rss-feed-translator/report.html)

## ドキュメント

- [設計ドキュメント](docs/superpowers/specs/2026-06-29-rss-feed-translator-design.md) — アーキテクチャ・セットアップ・設定・開発コマンド
- [実装計画](docs/superpowers/plans/2026-06-29-rss-feed-translator.md) — 初回実装のタスクリスト
- [用語定義](docs/glossary.md) — ドメイン用語・命名規則
