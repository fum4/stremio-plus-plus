"""Cache cleanup, per torrent: drop what hasn't been played (or downloaded) for 7 days, then evict
least-recently-used torrents while the disk is under the reserve. Live engines are never touched.

Per torrent, not per episode: the server keeps a per-torrent piece bitfield, so deleting one file of
a pack would leave the bitfield claiming data that is gone (docs/work/backlog.md).
"""

import re
from dataclasses import dataclass
from pathlib import Path

_INFO_HASH = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class CachedTorrent:
    info_hash: str
    path: Path
    size_bytes: int
    last_used: float


def scan_cache(cache_dir: Path, last_played: dict[str, float]) -> list[CachedTorrent]:
    torrents: list[CachedTorrent] = []
    if not cache_dir.is_dir():
        return torrents
    for entry in cache_dir.iterdir():
        if not (entry.is_dir() and _INFO_HASH.match(entry.name)):
            continue
        files = [p for p in entry.rglob("*") if p.is_file()]
        # st_blocks: torrent files are sparse until complete; count what is really on disk.
        size = sum(p.stat().st_blocks * 512 for p in files)
        newest_write = max((p.stat().st_mtime for p in files), default=entry.stat().st_mtime)
        torrents.append(
            CachedTorrent(
                entry.name, entry, size, max(newest_write, last_played.get(entry.name, 0.0))
            )
        )
    return torrents


def plan_cleanup(
    torrents: list[CachedTorrent],
    active: set[str],
    *,
    now: float,
    free_bytes: int,
    stale_after_s: float,
    min_free_bytes: int,
) -> list[CachedTorrent]:
    idle = sorted((t for t in torrents if t.info_hash not in active), key=lambda t: t.last_used)
    doomed = [t for t in idle if now - t.last_used > stale_after_s]
    free_after = free_bytes + sum(t.size_bytes for t in doomed)
    for torrent in idle:
        if free_after >= min_free_bytes:
            break
        if torrent not in doomed:
            doomed.append(torrent)
            free_after += torrent.size_bytes
    return doomed
