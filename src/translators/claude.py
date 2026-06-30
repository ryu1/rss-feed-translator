from __future__ import annotations

import logging
import os

import anthropic

from src.exceptions import TranslationError

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_BEDROCK_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


class ClaudeTranslator:
    def __init__(
        self,
        model: str | None = None,
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

    _SEP = "<<<TRANSLATION_SEP>>>"

    def translate(self, texts: list[str], target_lang: str = "ja") -> list[str]:
        if not texts:
            return []
        joined = f"\n{self._SEP}\n".join(texts)
        sep = self._SEP
        prompt = (
            f"Translate each section separated by '{sep}' into {target_lang}. "
            f"Return only the translations separated by '\\n{sep}\\n', "
            "in the same order. "
            "Do not add any explanation.\n\n" + joined
        )
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            text_blocks = [
                block
                for block in response.content
                if isinstance(block, anthropic.types.TextBlock)
            ]
            content = text_blocks[0].text if text_blocks else ""
            parts = [t.strip() for t in content.split(f"\n{self._SEP}\n")]
            if len(parts) != len(texts):
                msg = f"Expected {len(texts)} translations, got {len(parts)}"
                raise TranslationError(msg)
            return parts
        except TranslationError:
            raise
        except Exception as e:
            raise TranslationError(f"Claude translation error: {e}") from e
