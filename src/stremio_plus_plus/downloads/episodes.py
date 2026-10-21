"""Find the next episode inside the same torrent (season packs)."""

import re

from stremio_plus_plus.downloads.constants import VIDEO_EXTENSIONS
from stremio_plus_plus.server.models import Engine, TorrentFile

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


def next_episodes(engine: Engine, file_index: int, count: int | None) -> list[TorrentFile]:
    """The episodes after the playing one, in order: `count` of them (crossing into the next
    season), or with `count=None` the rest of the current season."""
    current = engine.file(file_index)
    parsed = parse_episode(current.name) if current else None
    if parsed is None or count == 0:
        return []
    by_key: dict[tuple[int, int], tuple[tuple[int, int], TorrentFile]] = {}
    for f in engine.files:
        key = parse_episode(f.name) if _is_video(f) else None
        # The largest file per episode: packs carry samples/extras with the same tag.
        if (
            key is not None
            and key > parsed
            and (key not in by_key or f.length > by_key[key][1].length)
        ):
            by_key[key] = (key, f)
    later = [by_key[k] for k in sorted(by_key)]
    if count is None:
        return [f for (season, _), f in later if season == parsed[0]]
    return [f for _, f in later[:count]]
