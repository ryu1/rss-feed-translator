from __future__ import annotations

import json
import logging
import os

import anthropic

from src.exceptions import SummarizationError
from src.models import Article
from src.summarizer import DEFAULT_SUMMARIZER_PROMPT

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_BEDROCK_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


class ClaudeSummarizer:
    def __init__(
        self,
        model: str | None = None,
        prompt_template: str = DEFAULT_SUMMARIZER_PROMPT,
        provider: str = "anthropic",
    ) -> None:
        if provider == "bedrock":
            bedrock_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
            if not bedrock_token:
                raise ValueError(
                    "AWS_BEARER_TOKEN_BEDROCK environment variable not set"
                )
            self._client: anthropic.Anthropic | anthropic.AnthropicBedrock = (
                anthropic.AnthropicBedrock(api_key=bedrock_token)
            )
            self._model = model or _DEFAULT_BEDROCK_MODEL
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self._client = anthropic.Anthropic(api_key=api_key)
            self._model = model or _DEFAULT_MODEL
        self._prompt_template = prompt_template

    def summarize(self, article: Article) -> tuple[str, str]:
        safe_title = article.title.replace("{", "{{").replace("}", "}}")
        safe_description = article.description.replace("{", "{{").replace("}", "}}")
        safe_source = article.source.replace("{", "{{").replace("}", "}}")
        prompt = self._prompt_template.format(
            title=safe_title,
            description=safe_description,
            source=safe_source,
        )
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            text_blocks = [
                block
                for block in response.content
                if isinstance(block, anthropic.types.TextBlock)
            ]
            content = text_blocks[0].text if text_blocks else "{}"
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end == 0:
                raise SummarizationError("No JSON found in Claude response")
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
