"""Reacts to playback: keep the playing file downloading, prefetch the next episode, release
pins once files are complete."""

import asyncio
from collections.abc import Callable

import httpx
import structlog

from stremio_plus_plus.downloads.constants import (
    COMPLETE_PROGRESS,
    PIN_SWEEP_INTERVAL_S,
)
from stremio_plus_plus.downloads.episodes import next_episodes
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.watch.events import EngineDestroyed, Event, FileRequested

log = structlog.get_logger()
# (info_hash, playing file index, next file index, next file name, next file length, distance:
# 1 = the very next episode)
NextEpisodeHook = Callable[[str, int, int, str, int, int], None]
# (episodes to download ahead, None = rest of the season; how many of those to subtitle ahead)
Lookahead = Callable[[], tuple[int | None, int]]


class DownloadManager:
    def __init__(
        self,
        server: StremioServer,
        pinner: Pinner,
        free_bytes: Callable[[], int],
        min_free_bytes: Callable[[], int],  # read per decision: follows config.toml edits
        on_next_episode: NextEpisodeHook | None = None,
        lookahead: Lookahead = lambda: (1, 1),
    ) -> None:
        self._server = server
        self._pinner = pinner
        self._free_bytes = free_bytes
        self._on_next_episode = on_next_episode  # e.g. subtitles for it, ahead of time
        self._min_free_bytes = min_free_bytes
        self._lookahead = lookahead

    async def __call__(self, event: Event) -> None:
        if isinstance(event, EngineDestroyed):
            await self._pinner.release_engine(event.info_hash)
        elif isinstance(event, FileRequested):
            await self._on_play(event)

    async def _on_play(self, event: FileRequested) -> None:
        engine = (await self._server.engines()).get(event.info_hash)
        if engine is None or engine.file(event.file_index) is None:
            return
        if (
            await self._server.file_progress(event.info_hash, event.file_index) or 0
        ) < COMPLETE_PROGRESS:
            self._pinner.pin(event.info_hash, event.file_index)
        downloads, subtitles = self._lookahead()
        upcoming = next_episodes(engine, event.file_index, downloads)
        if self._on_next_episode is not None:
            for distance, nxt in enumerate(upcoming[:subtitles], start=1):
                self._on_next_episode(
                    event.info_hash, event.file_index, nxt.index, nxt.name, nxt.length, distance
                )
        free, queued = self._free_bytes(), 0  # each extra episode must still leave the reserve
        for nxt in upcoming:
            pinned = (event.info_hash, nxt.index) in self._pinner.pinned()
            if not pinned:
                progress = await self._server.file_progress(event.info_hash, nxt.index) or 0
                if progress >= COMPLETE_PROGRESS:
                    continue
            if free - queued - nxt.length < self._min_free_bytes():
                log.warning(
                    "prefetch_skipped_low_disk", next=nxt.name, free_gb=round(free / 1024**3, 1)
                )
                break
            queued += nxt.length
            if not pinned and self._pinner.pin(event.info_hash, nxt.index):
                log.info("prefetch_next_episode", next=nxt.name)

    async def sweep(self) -> None:
        for info_hash, file_index in sorted(self._pinner.pinned()):
            try:
                progress = await self._server.file_progress(info_hash, file_index)
            except httpx.TimeoutException:  # server busy streaming: check this file next sweep
                log.warning("pin_progress_timeout", info_hash=info_hash, file_index=file_index)
                continue
            if progress is None or progress >= COMPLETE_PROGRESS:
                reason = "torrent closed" if progress is None else "complete"
                await self._pinner.release(info_hash, file_index, reason)

    async def run_sweeper(self, interval_s: float = PIN_SWEEP_INTERVAL_S) -> None:
        while True:
            await asyncio.sleep(interval_s)
            try:
                await self.sweep()
            except Exception:  # the sweeper must outlive a transient server error
                log.exception("pin_sweep_failed")
