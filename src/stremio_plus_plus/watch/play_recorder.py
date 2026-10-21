"""Records every TV read in `file_plays` (last played time + offset)."""

import time
from collections.abc import Callable

import structlog

from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.plays import FilePlay, Plays
from stremio_plus_plus.watch.events import Event, FileRequested

log = structlog.get_logger()


class PlayRecorder:
    def __init__(
        self, server: StremioServer, plays: Plays, clock: Callable[[], float] = time.time
    ) -> None:
        self._server = server
        self._plays = plays
        self._clock = clock

    async def __call__(self, event: Event) -> None:
        if not isinstance(event, FileRequested):
            return
        engine = (await self._server.engines()).get(event.info_hash)
        file = engine.file(event.file_index) if engine else None
        if file is None:
            return
        self._plays.record(
            FilePlay(
                event.info_hash,
                event.file_index,
                file.name,
                file.length,
                event.offset,
                self._clock(),
            )
        )
        log.info(
            "tv_read",
            file=file.name,
            offset=event.offset,
            progress=round(event.offset / max(file.length, 1), 3),
        )
