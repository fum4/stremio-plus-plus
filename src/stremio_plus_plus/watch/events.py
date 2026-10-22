"""Parse Stremio server log lines into playback events.

server.js logs one line per HTTP request (`-> GET /<ih>/<idx>[?query] bytes=<start>-[end]`) and
engine lifecycle lines. That log is the only place the TV's reads are visible (format verified
against server.js v4.22.4, docs/research/stremio-internals.md).
"""

import re
from dataclasses import dataclass
from urllib.parse import unquote

from stremio_plus_plus.server.constants import COMPANION_TAG

_FILE_REQUEST = re.compile(
    r"^-> GET /(?P<ih>[0-9a-f]{40})/(?P<idx>\d+)(?P<query>\?\S*)?(?: bytes=(?P<start>\d+)-\d*)?\s*$"
)
_SUBTITLE_FETCH = re.compile(r"^-> GET /subtitles\.\w+\?(?:\S*&)?from=(?P<src>[^&\s]+)")
# Any other request; untagged ones come from a Stremio app (the TV), never from the companion.
_REQUEST = re.compile(r"^-> [A-Z]+ (?P<path>/\S*)")
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


@dataclass(frozen=True)
class SubtitleFetched:
    """The player loaded an external subtitle track (any addon's) through the server."""

    source_url: str


@dataclass(frozen=True)
class ClientSeen:
    """A Stremio app talked to the server (settings, stats…): it is pointed at this host."""

    path: str


Event = FileRequested | EngineCreated | EngineDestroyed | SubtitleFetched | ClientSeen


def parse_line(line: str) -> Event | None:
    line = line.strip()
    if m := _FILE_REQUEST.match(line):
        if COMPANION_TAG in (m["query"] or ""):
            return None
        return FileRequested(m["ih"], int(m["idx"]), int(m["start"] or 0))
    if m := _SUBTITLE_FETCH.match(line):
        return SubtitleFetched(unquote(m["src"]))
    if m := _ENGINE_CREATED.match(line):
        return EngineCreated(m["ih"])
    if m := _ENGINE_DESTROYED.match(line):
        return EngineDestroyed(m["ih"])
    if (m := _REQUEST.match(line)) and COMPANION_TAG not in m["path"]:
        return ClientSeen(m["path"].split("?", 1)[0])
    return None
