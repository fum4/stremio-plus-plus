"""All HLS sessions, by source key; stops the producers of the ones the player has left."""

import asyncio
import shutil
import time
from collections.abc import Callable
from pathlib import Path

import structlog

from stremio_plus_plus.stream.constants import IDLE_STOP_S
from stremio_plus_plus.stream.session import Session, Source

log = structlog.get_logger()


class Sessions:
    def __init__(self, work_dir: Path, clock: Callable[[], float] = time.monotonic) -> None:
        self._dir = work_dir
        self._clock = clock
        self._sources: dict[str, Source] = {}
        self._live: dict[str, Session] = {}
        shutil.rmtree(work_dir, ignore_errors=True)  # segments of a previous run are useless

    def offer(self, source: Source) -> None:
        """Remember a source handed to the player, so its playlist URLs resolve later."""
        self._sources[source.key] = source

    def get(self, key: str) -> Session | None:
        session = self._live.get(key)
        if session is None and (source := self._sources.get(key)) is not None:
            session = self._live[key] = Session(source, self._dir / key, self._clock)
            log.info("stream_session_started", file=source.file_name)
        return session

    def playing(self, info_hash: str, file_index: int) -> Session | None:
        """The live session reading this torrent file, if the player is still on it."""
        for session in self._live.values():
            source = session.source
            same = (source.info_hash, source.file_index) == (info_hash, file_index)
            if same and self._clock() - session.last_request < IDLE_STOP_S:
                return session
        return None

    def live(self) -> list[Session]:
        return list(self._live.values())

    async def run_reaper(self, every_s: float = 30.0) -> None:
        while True:
            await asyncio.sleep(every_s)
            now = self._clock()
            for session in list(self._live.values()):
                if now - session.last_request > IDLE_STOP_S and await session.stop():
                    # Kept: its probe and subtitle choice survive a long pause.
                    log.info("stream_session_idle", file=session.source.file_name)

    async def close(self) -> None:
        for session in list(self._live.values()):
            await session.stop()
        self._live.clear()
