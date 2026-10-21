"""EN → RO translation with Claude Haiku through the `claude` CLI on the owner's subscription.

Guardrails (personal use of a consumer plan): one call at a time, a hard hourly cap, no tools,
no settings, no MCP, no session persistence. The model sees numbered lines only, never timings.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Protocol, cast

import structlog

from stremio_companion.subtitles.constants import (
    CLAUDE_TIMEOUT_S,
    CONTEXT_CUES,
    MAX_CLAUDE_CALLS_PER_HOUR,
    TRANSLATE_MODEL,
)

log = structlog.get_logger()

SYSTEM_PROMPT = (
    "You translate English TV subtitles into natural, idiomatic Romanian as a professional "
    "subtitler would: correct diacritics (ă â î ș ț), concise, colloquial where the speech is, "
    "keep names, keep profanity at the same strength. You get numbered lines; return exactly one "
    "translation per id, same ids, no merging or splitting. Lines given as context are earlier, "
    "already-translated subtitles: use them only for continuity."
)
SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "cues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "ro": {"type": "string"}},
                    "required": ["id", "ro"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["cues"],
        "additionalProperties": False,
    }
)


class Translator(Protocol):
    async def translate(self, lines: list[str], context: list[str]) -> list[str]: ...


def build_prompt(lines: list[str], context: list[str]) -> str:
    ctx = "\n".join(context[-CONTEXT_CUES:])
    body = "\n".join(f"{i}: {line}" for i, line in enumerate(lines, 1))
    return (
        f"Context (earlier subtitles, already translated):\n{ctx}\n\n" if ctx else ""
    ) + f"Translate:\n{body}"


def parse_response(stdout: str, expected: int) -> list[str] | None:
    try:
        data = cast(dict[str, Any], json.loads(stdout))
    except json.JSONDecodeError:
        return None
    output = cast(dict[str, Any], data.get("structured_output") or {})
    got = {int(c["id"]): str(c["ro"]) for c in cast(list[dict[str, Any]], output.get("cues") or [])}
    if all(i in got for i in range(1, expected + 1)):
        return [got[i] for i in range(1, expected + 1)]
    return None


class ClaudeCliTranslator:
    def __init__(
        self, claude_bin: Path, max_calls_per_hour: int = MAX_CLAUDE_CALLS_PER_HOUR
    ) -> None:
        self._bin = claude_bin
        self._max_calls = max_calls_per_hour
        self._calls: list[float] = []
        self._lock = asyncio.Lock()

    async def translate(self, lines: list[str], context: list[str]) -> list[str]:
        if not lines:
            return []
        prompt = build_prompt(lines, context)
        for attempt in range(3):
            stdout = await self._call(prompt)
            if (parsed := parse_response(stdout, len(lines))) is not None:
                return parsed
            log.warning("translate_retry", attempt=attempt, lines=len(lines))
        log.error("translate_failed_keeping_english", lines=len(lines))
        return lines

    async def _call(self, prompt: str) -> str:
        async with self._lock:
            await self._wait_for_slot()
            proc = await asyncio.create_subprocess_exec(
                str(self._bin),
                "-p",
                "--model",
                TRANSLATE_MODEL,
                "--tools",
                "",
                "--strict-mcp-config",
                "--setting-sources",
                "",
                "--no-session-persistence",
                "--system-prompt",
                SYSTEM_PROMPT,
                "--json-schema",
                SCHEMA,
                "--output-format",
                "json",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                out, _ = await asyncio.wait_for(proc.communicate(prompt.encode()), CLAUDE_TIMEOUT_S)
            except TimeoutError:
                proc.kill()
                await proc.wait()
                return ""
            return out.decode(errors="replace")

    async def _wait_for_slot(self) -> None:
        while True:
            now = time.time()
            self._calls = [t for t in self._calls if now - t < 3600]
            if len(self._calls) < self._max_calls:
                self._calls.append(now)
                return
            log.warning("claude_hourly_cap_reached", calls=len(self._calls))
            await asyncio.sleep(60)
