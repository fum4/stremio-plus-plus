"""Reacts to playback: keep the playing file downloading, prefetch the next episode, release
pins once files are complete."""

import asyncio
from collections.abc import Callable

import structlog

from stremio_companion.downloads.constants import (
    COMPLETE_PROGRESS,
    MIN_FREE_BYTES,
    PIN_SWEEP_INTERVAL_S,
)
from stremio_companion.downloads.episodes import next_episode
from stremio_companion.downloads.pins import Pinner
from stremio_companion.server.client import StremioServer
from stremio_companion.watch.events import EngineDestroyed, Event, FileRequested

log = structlog.get_logger()


class DownloadManager:
    def __init__(
        self, server: StremioServer, pinner: Pinner, free_bytes: Callable[[], int]
    ) -> None:
        self._server = server
        self._pinner = pinner
        self._free_bytes = free_bytes

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
        if nxt is None or (event.info_hash, nxt.index) in self._pinner.pinned():
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
            progress = await self._server.file_progress(info_hash, file_index)
            if progress is None or progress >= COMPLETE_PROGRESS:
                await self._pinner.release(info_hash, file_index)

    async def run_sweeper(self, interval_s: float = PIN_SWEEP_INTERVAL_S) -> None:
        while True:
            await asyncio.sleep(interval_s)
            try:
                await self.sweep()
            except Exception:  # the sweeper must outlive a transient server error
                log.exception("pin_sweep_failed")
