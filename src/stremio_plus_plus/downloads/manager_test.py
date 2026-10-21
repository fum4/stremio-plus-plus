import asyncio

import pytest

from stremio_plus_plus.downloads.constants import MIN_FREE_BYTES
from stremio_plus_plus.downloads.fake_server_test_support import FakeServer
from stremio_plus_plus.downloads.manager import DownloadManager
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.watch.events import EngineDestroyed, FileRequested

IH = "aa" * 20
GB = 1024**3
STATS = {
    IH: {
        "name": "Show S01",
        "files": [
            {"name": "Show.S01E01.mkv", "length": 2 * GB},
            {"name": "Show.S01E02.mkv", "length": 2 * GB},
            {"name": "Show.S01E03.mkv", "length": 2 * GB},
        ],
    }
}


def _manager(
    progress: dict[tuple[str, int], float], free: int
) -> tuple[DownloadManager, Pinner, FakeServer]:
    fake = FakeServer(STATS, progress)
    pinner = Pinner(fake.http, fake.client)
    return DownloadManager(fake.client, pinner, lambda: free), pinner, fake


@pytest.mark.asyncio
async def test_playing_e01_pins_it_and_prefetches_e02() -> None:
    manager, pinner, _ = _manager({}, free=100 * GB)
    await manager(FileRequested(IH, 0, 0))
    assert pinner.pinned() == {(IH, 0), (IH, 1)}
    await pinner.close()


@pytest.mark.asyncio
async def test_no_prefetch_when_disk_would_drop_below_the_reserve() -> None:
    manager, pinner, _ = _manager({}, free=MIN_FREE_BYTES + GB)
    await manager(FileRequested(IH, 0, 0))
    assert pinner.pinned() == {(IH, 0)}
    await pinner.close()


@pytest.mark.asyncio
async def test_complete_files_are_not_pinned_and_sweep_releases_finished_pins() -> None:
    progress = {(IH, 0): 1.0}
    manager, pinner, _ = _manager(progress, free=100 * GB)
    await manager(FileRequested(IH, 0, 0))
    assert pinner.pinned() == {(IH, 1)}  # E01 already complete; E02 prefetched
    progress[(IH, 1)] = 1.0
    await asyncio.sleep(0.01)
    await manager.sweep()
    assert pinner.pinned() == set()


@pytest.mark.asyncio
async def test_a_busy_server_skips_one_file_not_the_whole_sweep() -> None:
    progress: dict[tuple[str, int], float] = {}
    manager, pinner, fake = _manager(progress, free=100 * GB)
    await manager(FileRequested(IH, 0, 0))
    assert pinner.pinned() == {(IH, 0), (IH, 1)}
    fake.busy.add((IH, 0))  # E01's progress check times out
    progress[(IH, 1)] = 1.0
    await asyncio.sleep(0.01)
    await manager.sweep()
    assert pinner.pinned() == {(IH, 0)}  # E02 still released; E01 checked next sweep
    await pinner.close()


@pytest.mark.asyncio
async def test_the_next_episode_is_announced_even_when_already_downloaded() -> None:
    fake = FakeServer(STATS, {(IH, 1): 1.0})
    pinner = Pinner(fake.http, fake.client)
    seen: list[tuple[str, int, int, str, int]] = []

    def hook(info_hash: str, playing: int, index: int, name: str, length: int) -> None:
        seen.append((info_hash, playing, index, name, length))

    manager = DownloadManager(fake.client, pinner, lambda: 100 * GB, hook)
    await manager(FileRequested(IH, 0, 0))
    assert seen == [(IH, 0, 1, "Show.S01E02.mkv", 2 * GB)]
    await pinner.close()


@pytest.mark.asyncio
async def test_engine_destroyed_drops_pins() -> None:
    manager, pinner, _ = _manager({}, free=100 * GB)
    await manager(FileRequested(IH, 1, 0))
    await manager(EngineDestroyed(IH))
    assert pinner.pinned() == set()
