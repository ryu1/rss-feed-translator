from __future__ import annotations

import logging
import time
from typing import Protocol

from src.exceptions import SummarizationError
from src.models import Article

logger = logging.getLogger(__name__)

DEFAULT_SUMMARIZER_PROMPT = """以下の英語のITニュース記事のタイトルと概要を読み、次のJSONを返してください。
{{
  "natural_title": "自然な日本語タイトル（直訳でなく読みやすく）",
  "summary": "1行目の要約。\\n2行目の要約。\\n3行目の要約。"
}}
タイトル: {title}
概要: {description}
ソース: {source}"""


class Summarizer(Protocol):
    def summarize(self, article: Article) -> tuple[str, str]: ...


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
                logger.error(
                    "Summarization failed after %d attempts for %s: %s",
                    max_attempts,
                    article.guid,
                    e,
                )
                return (None, None)
            wait = 2 ** (attempt - 1)
            logger.warning(
                "Summarization attempt %d/%d failed, retrying in %ds",
                attempt,
                max_attempts,
                wait,
            )
            time.sleep(wait)
    return (None, None)  # pragma: no cover


def get_summarizer(engine: str, model: str, prompt_template: str) -> Summarizer:
    if engine == "openai":
        from src.summarizers.openai import OpenAISummarizer

        return OpenAISummarizer(model=model, prompt_template=prompt_template)
    if engine == "claude":
        from src.summarizers.claude import ClaudeSummarizer

        return ClaudeSummarizer(model=model, prompt_template=prompt_template)
    raise ValueError(f"Unknown summarizer engine: {engine!r}. Choose from: openai, claude")
