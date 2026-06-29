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
