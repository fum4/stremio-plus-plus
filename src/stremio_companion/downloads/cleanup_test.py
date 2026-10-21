import os
from pathlib import Path

from stremio_companion.downloads.cleanup import CachedTorrent, plan_cleanup, scan_cache

DAY = 24 * 3600
NOW = 100 * DAY


def _t(name: str, last_used_days_ago: float, size: int = 10) -> CachedTorrent:
    return CachedTorrent(name * 40, Path("/x"), size, NOW - last_used_days_ago * DAY)


def _plan(
    torrents: list[CachedTorrent], active: set[str] | None = None, free: int = 1000
) -> list[str]:
    doomed = plan_cleanup(
        torrents,
        active or set(),
        now=NOW,
        free_bytes=free,
        stale_after_s=7 * DAY,
        min_free_bytes=100,
    )
    return [t.info_hash[0] for t in doomed]


def test_deletes_only_torrents_unused_for_more_than_7_days() -> None:
    assert _plan([_t("a", 8), _t("b", 6), _t("c", 30)]) == ["c", "a"]


def test_never_touches_active_engines_even_if_stale() -> None:
    assert _plan([_t("a", 30)], active={"a" * 40}) == []


def test_evicts_lru_while_under_the_disk_reserve() -> None:
    torrents = [_t("a", 1, size=50), _t("b", 2, size=50), _t("c", 3, size=50)]
    assert _plan(torrents, free=20) == ["c", "b"]  # 20 + 50 + 50 >= 100


def test_scan_cache_reads_sizes_and_uses_the_later_of_write_and_play(tmp_path: Path) -> None:
    ih = "ab" * 20
    (tmp_path / ih).mkdir()
    file = tmp_path / ih / "Show.S01E01.mkv"
    file.write_bytes(b"x" * 8192)
    os.utime(file, (1000.0, 1000.0))
    (tmp_path / "not-a-torrent").mkdir()
    [torrent] = scan_cache(tmp_path, {ih: 5000.0})
    assert torrent.info_hash == ih and torrent.size_bytes >= 8192 and torrent.last_used == 5000.0
    [stale] = scan_cache(tmp_path, {})
    assert stale.last_used == 1000.0
