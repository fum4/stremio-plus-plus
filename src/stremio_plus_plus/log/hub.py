"""Every log line the UI can show, in memory: the streaming server's (as the companion tails it)
and the companion's own events (a structlog processor). Secrets are redacted on the way in.

Server lines carry no timestamp of their own, so they're stamped on arrival; lines seeded from
the file at startup have none.
"""

import json
import re
import time
from collections import deque
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

Source = Literal["server", "companion"]
MAX_ENTRIES = 20_000
# server.js prints the account's authKey on /get-https; API keys and tokens never belong in a view.
_PATTERNS = (
    re.compile(r"(authKey[\"']?\s*[=:]\s*[\"']?)[^&\s\"',}]+"),
    re.compile(r"sk-ant-[A-Za-z0-9_\-]+"),
)


@dataclass(frozen=True)
class Entry:
    seq: int
    ts: float | None
    source: Source
    level: str
    text: str
    event: str | None = None  # companion events: the structlog event name
    fields: dict[str, Any] = field(default_factory=dict[str, Any])


class LogHub:
    def __init__(self, max_entries: int = MAX_ENTRIES) -> None:
        self._entries: deque[Entry] = deque(maxlen=max_entries)
        self._seq = 0
        self._secrets: set[str] = set()
        self.listeners: list[Callable[[Entry], None]] = []

    def add_secret(self, secret: str) -> None:
        if len(secret) >= 8:
            self._secrets.add(secret)

    def redact(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, "[redacted]")
        text = _PATTERNS[0].sub(r"\1[redacted]", text)
        return _PATTERNS[1].sub("sk-ant-[redacted]", text)

    def _add(self, entry: Entry) -> Entry:
        self._entries.append(entry)
        for listener in self.listeners:
            listener(entry)
        return entry

    def server_line(self, text: str, ts: float | None = None, *, notify: bool = True) -> None:
        self._seq += 1
        level = "error" if "error" in text.lower() else "info"
        entry = Entry(self._seq, ts, "server", level, self.redact(text))
        if notify:
            self._add(entry)
        else:
            self._entries.append(entry)

    def companion_event(self, event: MutableMapping[str, Any], *, notify: bool = True) -> None:
        name = str(event.get("event", ""))
        fields = {
            k: self.redact(str(v)) if isinstance(v, str) else v
            for k, v in event.items()
            if k not in {"event", "level", "timestamp", "exception"}
        }
        if exc := event.get("exception"):
            fields["exception"] = self.redact(str(exc))[-4000:]
        self._seq += 1
        entry = Entry(
            self._seq,
            _ts(event.get("timestamp")),
            "companion",
            str(event.get("level", "info")),
            self.redact(name),
            name,
            fields,
        )
        if notify:
            self._add(entry)
        else:
            self._entries.append(entry)

    def since(self, seq: int, limit: int) -> list[Entry]:
        newer = [e for e in self._entries if e.seq > seq]
        return newer[-limit:]

    def capture(self, _logger: object, _method: str, event: MutableMapping[str, Any]) -> Any:  # noqa: ANN401
        """structlog processor: copy every companion event into the hub, pass it on unchanged."""
        self.companion_event(event)
        return event


def _ts(value: object) -> float:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    return time.time()


def _tail(path: Path, max_bytes: int) -> list[str]:
    try:
        with path.open("rb") as f:
            size = f.seek(0, 2)
            f.seek(max(0, size - max_bytes))
            data = f.read().decode(errors="replace")
    except OSError:
        return []
    lines = data.splitlines()
    return lines[1:] if size > max_bytes else lines  # the first one is probably cut


def seed(hub: LogHub, server_log: Path, companion_log: Path, max_bytes: int = 1_000_000) -> None:
    """History from before this process started: the end of both files, without notifying."""
    for line in _tail(companion_log, max_bytes):
        try:
            event = cast(dict[str, Any], json.loads(line))
        except ValueError:
            continue
        hub.companion_event(event, notify=False)
    for line in _tail(server_log, max_bytes):
        hub.server_line(line, notify=False)


HUB = LogHub()
