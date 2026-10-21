from typing import Any

import pytest

from stremio_plus_plus.subtitles.translators.base import (
    HourlyCap,
    LlmTranslator,
    TranslatorConfigError,
    TranslatorStats,
)


class FakeBackend:
    def __init__(self, *replies: dict[str, Any] | Exception | None) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    async def complete(
        self, system: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any] | None:
        self.prompts.append(prompt)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _translator(backend: FakeBackend) -> tuple[LlmTranslator, TranslatorStats]:
    stats = TranslatorStats()
    return LlmTranslator(backend, HourlyCap(100), 15, stats), stats


@pytest.mark.asyncio
async def test_retries_a_bad_reply_then_succeeds() -> None:
    good = {"cues": [{"id": 1, "ro": "Salut."}]}
    translator, stats = _translator(FakeBackend(None, good))
    assert await translator.translate(["Hi."], []) == ["Salut."]
    assert stats.calls == 2 and stats.last_error is None


@pytest.mark.asyncio
async def test_keeps_the_original_after_three_bad_replies() -> None:
    translator, stats = _translator(FakeBackend(None, {"cues": []}, None))
    assert await translator.translate(["Hi."], []) == ["Hi."]
    assert stats.failures == 1 and stats.last_error


@pytest.mark.asyncio
async def test_unavailable_provider_fails_the_chunk() -> None:
    translator, stats = _translator(FakeBackend(TranslatorConfigError("no key")))
    with pytest.raises(TranslatorConfigError):
        await translator.translate(["Hi."], [])
    assert stats.last_error == "no key"


def test_hourly_cap_forgets_calls_older_than_an_hour() -> None:
    now = [10_000.0]
    cap = HourlyCap(2, clock=lambda: now[0], calls=[now[0] - 4000, now[0] - 10])
    assert cap.used() == 1
