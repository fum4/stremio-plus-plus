"""Backend: the Claude API with the user's own key (`anthropic` SDK, structured outputs)."""

import json
from typing import Any, cast

import anthropic

from stremio_plus_plus.subtitles.translators.base import TranslatorConfigError

MAX_TOKENS = 16000


class AnthropicBackend:
    def __init__(self, api_key: str | None, model: str, timeout_s: float) -> None:
        self._model = model
        self._client = (
            anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout_s, max_retries=2)
            if api_key
            else None
        )

    async def complete(
        self, system: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any] | None:
        if self._client is None:
            raise TranslatorConfigError("no Anthropic API key set")
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.AuthenticationError as exc:
            raise TranslatorConfigError("the Anthropic API key was rejected") from exc
        except anthropic.PermissionDeniedError as exc:
            raise TranslatorConfigError("the Anthropic API key lacks permission") from exc
        except anthropic.NotFoundError as exc:
            raise TranslatorConfigError(f"unknown model {self._model!r}") from exc
        except anthropic.APIStatusError, anthropic.APIConnectionError:
            return None  # 429/5xx/network after the SDK's own retries: retry the batch
        if response.stop_reason != "end_turn":
            return None
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return cast(dict[str, Any], json.loads(text))
        except json.JSONDecodeError:
            return None
