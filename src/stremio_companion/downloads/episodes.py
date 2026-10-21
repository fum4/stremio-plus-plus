"""Find the next episode inside the same torrent (season packs)."""

import re

from stremio_companion.downloads.constants import VIDEO_EXTENSIONS
from stremio_companion.server.models import Engine, TorrentFile

_PATTERNS = (
    re.compile(r"[Ss](?P<s>\d{1,2})[ ._-]?[Ee](?P<e>\d{1,3})(?!\d)"),
    re.compile(r"(?<!\d)(?P<s>\d{1,2})x(?P<e>\d{2,3})(?!\d)"),
)


def parse_episode(name: str) -> tuple[int, int] | None:
    base = name.rsplit("/", 1)[-1]
    for pattern in _PATTERNS:
        if m := pattern.search(base):
            return int(m["s"]), int(m["e"])
    return None


def _is_video(file: TorrentFile) -> bool:
    return file.name.lower().endswith(VIDEO_EXTENSIONS)


def next_episode(engine: Engine, file_index: int) -> TorrentFile | None:
    current = engine.file(file_index)
    parsed = parse_episode(current.name) if current else None
    if parsed is None:
        return None
    season, episode = parsed
    # Largest file wins when a pack carries samples/extras with the same episode tag.
    for key in ((season, episode + 1), (season + 1, 1)):
        same = [f for f in engine.files if _is_video(f) and parse_episode(f.name) == key]
        if same:
            return max(same, key=lambda f: f.length)
    return None
