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


class ClaudeSummarizer:
    def __init__(
        self, model: str = "claude-haiku-4-5-20251001", prompt_template: str = DEFAULT_PROMPT
    ) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set")
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._prompt_template = prompt_template

    def summarize(self, article: Article) -> tuple[str, str]:
        prompt = self._prompt_template.format(
            title=article.title,
            description=article.description,
            source=article.source,
        )
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            import anthropic as _anthropic

            text_blocks = [
                block for block in response.content if isinstance(block, _anthropic.types.TextBlock)
            ]
            content = text_blocks[0].text if text_blocks else "{}"
            start = content.find("{")
            end = content.rfind("}") + 1
            data = json.loads(content[start:end])
            natural_title: str = data.get("natural_title", "")
            summary: str = data.get("summary", "")
            if not natural_title or not summary:
                raise SummarizationError("Empty response from Claude summarizer")
            return (natural_title, summary)
        except SummarizationError:
            raise
        except Exception as e:
            raise SummarizationError(f"Claude summarization error: {e}") from e
