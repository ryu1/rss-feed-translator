from __future__ import annotations

import json
import logging
import os

from src.exceptions import SummarizationError
from src.models import Article

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = """以下の英語のITニュース記事のタイトルと概要を読み、次のJSONを返してください。
{{
  "natural_title": "自然な日本語タイトル（直訳でなく読みやすく）",
  "summary": "1行目の要約。\\n2行目の要約。\\n3行目の要約。"
}}
タイトル: {title}
概要: {description}
ソース: {source}"""


class OpenAISummarizer:
    def __init__(self, model: str = "gpt-4o-mini", prompt_template: str = DEFAULT_PROMPT) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._prompt_template = prompt_template

    def summarize(self, article: Article) -> tuple[str, str]:
        prompt = self._prompt_template.format(
            title=article.title,
            description=article.description,
            source=article.source,
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            natural_title: str = data.get("natural_title", "")
            summary: str = data.get("summary", "")
            if not natural_title or not summary:
                raise SummarizationError("Empty response from OpenAI summarizer")
            return (natural_title, summary)
        except SummarizationError:
            raise
        except Exception as e:
            raise SummarizationError(f"OpenAI summarization error: {e}") from e
