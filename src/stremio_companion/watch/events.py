"""Parse Stremio server log lines into playback events.

server.js logs one line per HTTP request (`-> GET /<ih>/<idx>[?query] bytes=<start>-[end]`) and
engine lifecycle lines. That log is the only place the TV's reads are visible (format verified
against server.js v4.22.4, docs/research/stremio-internals.md).
"""

import re
from dataclasses import dataclass

from stremio_companion.server.constants import COMPANION_TAG

_FILE_REQUEST = re.compile(
    r"^-> GET /(?P<ih>[0-9a-f]{40})/(?P<idx>\d+)(?P<query>\?\S*)?(?: bytes=(?P<start>\d+)-\d*)?\s*$"
)
_ENGINE_CREATED = re.compile(r"^Engine created for (?P<ih>[0-9a-f]{40})")
_ENGINE_DESTROYED = re.compile(r"^Engine (?P<ih>[0-9a-f]{40}) destroyed")


@dataclass(frozen=True)
class FileRequested:
    """The TV (never the companion: tagged requests are dropped) read a file from `offset`."""

    info_hash: str
    file_index: int
    offset: int


@dataclass(frozen=True)
class EngineCreated:
    info_hash: str


@dataclass(frozen=True)
class EngineDestroyed:
    info_hash: str


Event = FileRequested | EngineCreated | EngineDestroyed


def parse_line(line: str) -> Event | None:
    line = line.strip()
    if m := _FILE_REQUEST.match(line):
        if COMPANION_TAG in (m["query"] or ""):
            return None
        return FileRequested(m["ih"], int(m["idx"]), int(m["start"] or 0))
    if m := _ENGINE_CREATED.match(line):
        return EngineCreated(m["ih"])
    if m := _ENGINE_DESTROYED.match(line):
        return EngineDestroyed(m["ih"])
    return None
