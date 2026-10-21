"""Reacts to playback: keep the playing file downloading, prefetch the next episode, release
pins once files are complete."""

import asyncio
from collections.abc import Callable

import httpx
import structlog

from stremio_plus_plus.downloads.constants import (
    COMPLETE_PROGRESS,
    MIN_FREE_BYTES,
    PIN_SWEEP_INTERVAL_S,
)
from stremio_plus_plus.downloads.episodes import next_episode
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.watch.events import EngineDestroyed, Event, FileRequested

log = structlog.get_logger()
# (info_hash, playing file index, next file index, next file name, next file length)
NextEpisodeHook = Callable[[str, int, int, str, int], None]


class DownloadManager:
    def __init__(
        self,
        server: StremioServer,
        pinner: Pinner,
        free_bytes: Callable[[], int],
        on_next_episode: NextEpisodeHook | None = None,
    ) -> None:
        self._server = server
        self._pinner = pinner
        self._free_bytes = free_bytes
        self._on_next_episode = on_next_episode  # e.g. subtitles for it, ahead of time

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
        nxt = next_episode(engine, event.file_index)
        if nxt is None:
            return
        if self._on_next_episode is not None:
            self._on_next_episode(
                event.info_hash, event.file_index, nxt.index, nxt.name, nxt.length
            )
        if (event.info_hash, nxt.index) in self._pinner.pinned():
            return
        if (await self._server.file_progress(event.info_hash, nxt.index) or 0) >= COMPLETE_PROGRESS:
            return
        free = self._free_bytes()
        if free - nxt.length < MIN_FREE_BYTES:
            log.warning(
                "prefetch_skipped_low_disk", next=nxt.name, free_gb=round(free / 1024**3, 1)
            )
            return
        if self._pinner.pin(event.info_hash, nxt.index):
            log.info("prefetch_next_episode", next=nxt.name)

    async def sweep(self) -> None:
        for info_hash, file_index in sorted(self._pinner.pinned()):
            try:
                progress = await self._server.file_progress(info_hash, file_index)
            except httpx.TimeoutException:  # server busy streaming: check this file next sweep
                log.warning("pin_progress_timeout", info_hash=info_hash, file_index=file_index)
                continue
            if progress is None or progress >= COMPLETE_PROGRESS:
                await self._pinner.release(info_hash, file_index)

    async def run_sweeper(self, interval_s: float = PIN_SWEEP_INTERVAL_S) -> None:
        while True:
            await asyncio.sleep(interval_s)
            try:
                await self.sweep()
            except Exception:  # the sweeper must outlive a transient server error
                log.exception("pin_sweep_failed")
