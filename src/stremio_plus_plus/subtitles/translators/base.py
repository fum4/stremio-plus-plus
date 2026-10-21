"""The translator adapter: everything provider-neutral lives here, a backend only makes one call.

Adding a provider = one `Backend` (a class with `complete`) + one row in registry.py. Batching
prompts, validating replies, retries, the hourly cap and the keep-English fallback stay shared.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import structlog

from stremio_plus_plus.subtitles.translators.prompt import (
    SCHEMA,
    SYSTEM_PROMPT,
    build_prompt,
    parse_cues,
)

log = structlog.get_logger()
ATTEMPTS = 3


class Translator(Protocol):
    async def translate(self, lines: list[str], context: list[str]) -> list[str]: ...


class TranslatorConfigError(RuntimeError):
    """The provider can't work as configured (no key, bad key, unknown model, missing CLI).
    The chunk fails and is retried later; it is never stored untranslated."""


class Backend(Protocol):
    async def complete(
        self, system: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any] | None:
        """One model call. The parsed JSON reply, or None for a bad or empty reply."""
        ...


@dataclass
class HourlyCap:
    """At most `limit` calls in any rolling hour; callers wait for a slot. Shared across rebuilds
    of the backend, so editing the settings can't reset the budget."""

    limit: int
    clock: Callable[[], float] = time.time
    calls: list[float] = field(default_factory=list[float])

    def used(self) -> int:
        now = self.clock()
        self.calls = [t for t in self.calls if now - t < 3600]
        return len(self.calls)

    async def acquire(self) -> None:
        while self.used() >= self.limit:
            log.warning("translator_hourly_cap_reached", calls=len(self.calls))
            await asyncio.sleep(60)
        self.calls.append(self.clock())


@dataclass
class TranslatorStats:
    calls: int = 0
    failures: int = 0
    last_latency_s: float | None = None
    last_error: str | None = None


class LlmTranslator:
    def __init__(
        self,
        backend: Backend,
        cap: HourlyCap,
        context_cues: int,
        stats: TranslatorStats,
        lock: asyncio.Lock | None = None,  # shared across rebuilds: one call at a time, always
    ) -> None:
        self._backend = backend
        self._cap = cap
        self._context_cues = context_cues
        self._stats = stats
        self._lock = lock or asyncio.Lock()  # one call at a time: gentle on subscriptions

    async def translate(self, lines: list[str], context: list[str]) -> list[str]:
        if not lines:
            return []
        prompt = build_prompt(lines, context, self._context_cues)
        for attempt in range(ATTEMPTS):
            if (parsed := parse_cues(await self._call(prompt), len(lines))) is not None:
                return parsed
            log.warning("translate_retry", attempt=attempt, lines=len(lines))
        self._stats.failures += 1
        self._stats.last_error = "the model's reply was missing lines (kept the original text)"
        log.error("translate_failed_keeping_original", lines=len(lines))
        return lines

    async def _call(self, prompt: str) -> dict[str, Any] | None:
        async with self._lock:
            await self._cap.acquire()
            t0 = time.monotonic()
            try:
                out = await self._backend.complete(SYSTEM_PROMPT, prompt, SCHEMA)
            except TranslatorConfigError as exc:
                self._stats.failures += 1
                self._stats.last_error = str(exc)
                raise
            self._stats.calls += 1
            self._stats.last_latency_s = round(time.monotonic() - t0, 2)
            if out is not None:
                self._stats.last_error = None
            return out
