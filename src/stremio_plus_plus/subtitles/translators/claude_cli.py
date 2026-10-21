"""Backend: the `claude` CLI on the user's own Claude subscription (personal use).

Locked down: no tools, no settings, no MCP, no session persistence; the reply is forced into the
JSON schema by `--json-schema`.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, cast

from stremio_plus_plus.subtitles.translators.base import TranslatorConfigError


class ClaudeCliBackend:
    def __init__(self, claude_bin: Path, model: str, timeout_s: float) -> None:
        self._bin = claude_bin
        self._model = model
        self._timeout_s = timeout_s

    async def complete(
        self, system: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not os.access(self._bin, os.X_OK):
            raise TranslatorConfigError(f"claude CLI not found at {self._bin}")
        proc = await asyncio.create_subprocess_exec(
            str(self._bin),
            "-p",
            "--model",
            self._model,
            "--tools",
            "",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--no-session-persistence",
            "--system-prompt",
            system,
            "--json-schema",
            json.dumps(schema),
            "--output-format",
            "json",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(prompt.encode()), self._timeout_s)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return None
        return parse_cli_output(out.decode(errors="replace"))


def parse_cli_output(stdout: str) -> dict[str, Any] | None:
    try:
        data = cast(dict[str, Any], json.loads(stdout))
    except json.JSONDecodeError:
        return None
    if data.get("is_error") and "login" in str(data.get("result", "")).lower():
        raise TranslatorConfigError("the claude CLI is not logged in (run `claude` once)")
    return cast(dict[str, Any] | None, data.get("structured_output"))
