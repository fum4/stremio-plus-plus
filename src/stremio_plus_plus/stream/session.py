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
    FAILED_RETRY_S,
    KEEP_BEHIND_SEGMENTS,
    MAX_AHEAD_SEGMENTS,
    OLD_RUN_GRACE_S,
    POLL_S,
    RESTART_GAP_SEGMENTS,
    SEGMENT_S,
    SEGMENT_WAIT_S,
)
from stremio_plus_plus.stream.media import Media, probe
from stremio_plus_plus.stream.producer import Producer, segment_count, segment_path

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


def _serves(producer: Producer, index: int) -> bool:
    """This run has (or will soon write) segment `index`."""
    if producer.failed:
        return False
    return producer.kept_from <= index <= producer.head() + RESTART_GAP_SEGMENTS


def _remove(directory: Path) -> None:
    shutil.rmtree(directory, ignore_errors=True)


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
        self._tickets = 0  # one per segment request; the newest decides where the producer is
        self._lock = asyncio.Lock()
        self.last_request = clock()
        self.last_segment = 0  # newest video segment the player asked for
        self.last_reported = -1_000  # segment last reported to the playback handlers
        self.subtitles_on = False
        # Subtitle segments handed out since the last jump (a seek): the bridge track covers
        # exactly these when the viewer switches our subtitles on (app/subtitle_switch.py).
        self.vtt_run_start = 0.0
        self.vtt_served_until = 0.0
        self._last_vtt = -1

    def served_vtt(self, index: int) -> None:
        start, end = index * SEGMENT_S, (index + 1) * SEGMENT_S
        if index not in (self._last_vtt, self._last_vtt + 1):
            self.vtt_run_start, self.vtt_served_until = start, end  # a jump: a new run
        else:
            self.vtt_served_until = max(self.vtt_served_until, end)
        self._last_vtt = index

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
        if not 0 <= index < segment_count(media.duration_s):
            raise IndexError(index)
        self.touch()
        self.last_segment = index
        self._tickets += 1
        ticket = self._tickets
        deadline = self._clock() + SEGMENT_WAIT_S
        while True:
            async with self._lock:
                producer = self._producer
                if producer is None or not _serves(producer, index):
                    # Only the newest request may move the producer: a request the player gave
                    # up on (it seeked away) would otherwise drag it back and forth.
                    jumped = abs(index - self.last_segment) > RESTART_GAP_SEGMENTS
                    if ticket != self._tickets and jumped:
                        raise SegmentUnavailableError(f"segment {index}: superseded")
                    if (
                        producer is not None
                        and producer.failed
                        and producer.first == index
                        and self._clock() - producer.started_at < FAILED_RETRY_S
                    ):
                        raise SegmentUnavailableError(
                            f"segment {index}: ffmpeg exited {producer.returncode}"
                        )
                    producer = await self._restart(media, index)
                producer.pause(producer.head() > index + MAX_AHEAD_SEGMENTS)
                producer.forget_before(index - KEEP_BEHIND_SEGMENTS)
                if producer.finished(index):
                    return segment_path(producer.dir, index)
                if producer.done and not producer.failed:
                    raise SegmentUnavailableError(f"segment {index}: not in the output")
            if self._clock() > deadline:
                raise SegmentUnavailableError(f"segment {index}: timed out")
            await asyncio.sleep(POLL_S)

    async def _restart(self, media: Media, index: int) -> Producer:
        old = self._producer
        if old is not None:
            if old.failed:  # before stop(): our own SIGTERM is not a failure
                log.warning("stream_producer_failed", first=old.first, code=old.returncode)
            await old.stop()
            # Not deleted at once: a response may still be streaming one of its files.
            asyncio.get_running_loop().call_later(OLD_RUN_GRACE_S, _remove, old.dir)
        self._runs += 1
        producer = Producer(self.source.url, media, self._dir / f"run-{self._runs}", index)
        producer.started_at = self._clock()
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
