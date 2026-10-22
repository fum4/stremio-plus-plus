"""One source being watched as HLS: probes it, runs a Producer from wherever the player asks,
restarts it on a seek, paces it, and remembers what the subtitle track has handed out."""

import asyncio
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import structlog

from stremio_plus_plus.stream.constants import (
    KEEP_BEHIND_SEGMENTS,
    MAX_AHEAD_SEGMENTS,
    POLL_S,
    RESTART_GAP_SEGMENTS,
    SEGMENT_S,
    SEGMENT_WAIT_S,
)
from stremio_plus_plus.stream.media import Media, probe
from stremio_plus_plus.stream.producer import Producer, segment_path

log = structlog.get_logger()


@dataclass(frozen=True)
class Source:
    """What to play. Torrent files are read through the streaming server, so `url` is that."""

    key: str  # stable id, part of the playlist URLs
    url: str
    info_hash: str  # subtitle jobs and downloads are keyed by torrent file
    file_index: int
    file_name: str
    file_length: int


class SegmentUnavailableError(Exception):
    pass


class Session:
    def __init__(
        self, source: Source, work_dir: Path, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.source = source
        self._dir = work_dir
        self._clock = clock
        self._media: Media | None = None
        self._producer: Producer | None = None
        self._runs = 0
        self._lock = asyncio.Lock()
        self.last_request = clock()
        self.last_segment = 0  # newest video segment the player asked for
        self.subtitles_on = False
        self.vtt_served_until = 0.0  # end of the newest subtitle segment handed out

    async def media(self) -> Media:
        if self._media is None:
            async with self._lock:
                if self._media is None:
                    self._media = await probe(self.source.url)
                    log.info("stream_probed", file=self.source.file_name, **vars(self._media))
        return self._media

    @property
    def playhead_s(self) -> float:
        return self.last_segment * SEGMENT_S

    def touch(self) -> None:
        self.last_request = self._clock()

    async def segment(self, index: int) -> Path:
        media = await self.media()
        self.touch()
        self.last_segment = index
        deadline = self._clock() + SEGMENT_WAIT_S
        while True:
            async with self._lock:
                producer = await self._producer_for(media, index)
                producer.pause(producer.head() > index + MAX_AHEAD_SEGMENTS)
                producer.forget_before(index - KEEP_BEHIND_SEGMENTS)
                if producer.finished(index):
                    return segment_path(producer.dir, index)
                if producer.done:
                    raise SegmentUnavailableError(f"segment {index}: producer ended")
            if self._clock() > deadline:
                raise SegmentUnavailableError(f"segment {index}: timed out")
            await asyncio.sleep(POLL_S)

    async def _producer_for(self, media: Media, index: int) -> Producer:
        current = self._producer
        if (
            current is not None
            and not current.failed
            and current.kept_from <= index <= current.head() + RESTART_GAP_SEGMENTS
        ):
            return current
        if current is not None:
            await current.stop()
            shutil.rmtree(current.dir, ignore_errors=True)
        self._runs += 1
        producer = Producer(self.source.url, media, self._dir / f"run-{self._runs}", index)
        await producer.start()
        self._producer = producer
        return producer

    async def stop(self) -> bool:
        """Stop producing and drop the segments; True if a producer was running."""
        async with self._lock:
            if self._producer is None:
                return False
            await self._producer.stop()
            self._producer = None
            shutil.rmtree(self._dir, ignore_errors=True)
            return True
