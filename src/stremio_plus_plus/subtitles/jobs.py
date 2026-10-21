"""Generates Romanian subtitles window by window for the files the TV plays, playhead first.

Window sizes come from scheduler.py. Whisper (GPU) and Claude (network) are pipelined: the next
window is transcribed while the previous one is being translated, so one step costs about the
slower of the two instead of their sum.
"""

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

import structlog

from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.subtitles import audio
from stremio_plus_plus.subtitles.constants import (
    MAX_WINDOW_FAILURES,
    OVERLAP_S,
    RETRY_FAILED_AFTER_S,
    TAIL_READ_FRACTION,
)
from stremio_plus_plus.subtitles.cues import Cue
from stremio_plus_plus.subtitles.scheduler import Span, next_window
from stremio_plus_plus.subtitles.store import SubtitleFile, SubtitleStore
from stremio_plus_plus.subtitles.stt import Transcriber
from stremio_plus_plus.subtitles.translate import Translator
from stremio_plus_plus.watch.events import Event, FileRequested

log = structlog.get_logger()
FileKey = tuple[str, int]


@dataclass
class _Job:
    info_hash: str
    file_index: int
    file_name: str
    file_length: int
    playhead_fraction: float = (
        0.0  # of the file's bytes; kept as a fraction until the duration is known
    )
    last_active: float = 0.0
    meta: SubtitleFile | None = None
    failures: dict[Span, int] = field(default_factory=dict[Span, int])
    in_flight: list[Span] = field(default_factory=list[Span])
    dead: bool = False
    failed_at: float = 0.0

    def playhead_s(self) -> float:
        return self.playhead_fraction * (self.meta.duration_s if self.meta else 0.0)


class SubtitleJobs:
    def __init__(
        self,
        server: StremioServer,
        store: SubtitleStore,
        transcriber: Transcriber,
        translator: Translator,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._server = server
        self._store = store
        self._stt = transcriber
        self._translator = translator
        self._clock = clock
        self._jobs: dict[FileKey, _Job] = {}
        self._wake = asyncio.Event()

    def ensure(self, info_hash: str, file_index: int, file_name: str, file_length: int) -> None:
        """Called on every subtitles request; the job starts (or wakes) and gets priority."""
        key = (info_hash, file_index)
        job = self._jobs.get(key)
        if job is None:
            job = self._jobs[key] = _Job(info_hash, file_index, file_name, file_length)
            job.meta = self._store.file(info_hash, file_index)
        now = self._clock()
        if (job.dead or job.failures) and now - job.failed_at >= RETRY_FAILED_AFTER_S:
            job.dead = False  # the torrent may have found peers since: try again
            job.failures.clear()
        job.last_active = now
        self._wake.set()

    def cues(self, info_hash: str, file_index: int) -> list[Cue]:
        return self._store.cues(info_hash, file_index)

    def generating(self, info_hash: str, file_index: int) -> bool:
        job = self._jobs.get((info_hash, file_index))
        return job is not None and not job.dead

    async def __call__(self, event: Event) -> None:
        if not isinstance(event, FileRequested):
            return
        job = self._jobs.get((event.info_hash, event.file_index))
        if job is None or event.offset > job.file_length * TAIL_READ_FRACTION:
            return
        job.playhead_fraction = event.offset / max(job.file_length, 1)
        job.last_active = self._clock()
        self._wake.set()

    async def run(self) -> None:
        translating: asyncio.Task[None] | None = None
        try:
            while True:
                job, window = self._pick()
                if job is None:
                    if translating is not None:  # its window may unlock the next one
                        await translating
                        translating = None
                        continue
                    self._wake.clear()
                    await self._wake.wait()
                    continue
                if window is None:  # not probed yet
                    await self._guard(job, None, self._prepare(job))
                    continue
                job.in_flight.append(window)
                heard = await self._guard(job, window, self._hear(job, window))
                if translating is not None:  # in order: this window's context is that one
                    await translating
                    translating = None
                if heard is None:
                    job.in_flight.remove(window)
                    continue
                translating = asyncio.create_task(self._translate(job, window, heard))
        finally:
            if translating is not None:
                translating.cancel()

    async def _guard[T](
        self, job: _Job, window: Span | None, step: Coroutine[Any, Any, T]
    ) -> T | None:
        try:
            return await step
        except asyncio.CancelledError:
            raise
        except Exception:  # one bad window or file must not stop subtitles for everything else
            log.exception("subtitle_window_failed", file=job.file_name, window=window)
            job.failed_at = self._clock()
            if window is None:
                job.dead = True
            else:
                job.failures[window] = job.failures.get(window, 0) + 1
            return None

    def _pick(self) -> tuple[_Job | None, Span | None]:
        for job in sorted(self._jobs.values(), key=lambda j: j.last_active, reverse=True):
            if job.dead:
                continue
            if job.meta is None:
                return job, None  # probe first
            skipped = [w for w, n in job.failures.items() if n >= MAX_WINDOW_FAILURES]
            covered = self._store.spans(job.info_hash, job.file_index) + job.in_flight + skipped
            window = next_window(covered, job.meta.duration_s, job.playhead_s())
            if window is not None:
                return job, window
        return None, None

    async def _prepare(self, job: _Job) -> None:
        # Hash computed by the server from the file itself: a client-supplied hash could make
        # another file reuse the wrong subtitles.
        video_hash = await self._server.opensub_hash(job.info_hash, job.file_index)
        same = self._store.find_same_video(video_hash, job.file_length) if video_hash else None
        if same and (same.info_hash, same.file_index) != (job.info_hash, job.file_index):
            job.meta = SubtitleFile(
                job.info_hash,
                job.file_index,
                job.file_name,
                job.file_length,
                video_hash,
                same.duration_s,
                same.audio_stream,
                same.center,
            )
            self._store.save_file(job.meta)
            self._store.copy_spans(same, job.info_hash, job.file_index)
            log.info("subtitles_reused_from_same_video", file=job.file_name)
            return
        track = await audio.probe(self._server.file_url(job.info_hash, job.file_index))
        if track is None:
            job.dead = True
            job.failed_at = self._clock()
            log.warning("subtitles_no_audio", file=job.file_name)
            return
        job.meta = SubtitleFile(
            job.info_hash,
            job.file_index,
            job.file_name,
            job.file_length,
            video_hash,
            track.duration_s,
            track.stream,
            track.center,
        )
        self._store.save_file(job.meta)
        log.info(
            "subtitles_prepared",
            file=job.file_name,
            duration_s=track.duration_s,
            center=track.center,
        )

    async def _hear(self, job: _Job, window: Span) -> tuple[list[Cue], float]:
        """English cues starting inside the window, and when work on it started."""
        assert job.meta is not None
        t0 = self._clock()
        start, end = window
        read_from = max(0.0, start - OVERLAP_S)
        track = audio.AudioTrack(job.meta.audio_stream, job.meta.center, job.meta.duration_s)
        samples = await audio.read_chunk(
            self._server.file_url(job.info_hash, job.file_index), track, read_from, end - read_from
        )
        heard = await self._stt.transcribe(samples, read_from)
        return [c for c in heard if start <= c.start < end], t0

    async def _translate(self, job: _Job, window: Span, heard: tuple[list[Cue], float]) -> None:
        own, t0 = heard
        try:
            earlier = self._store.cues(job.info_hash, job.file_index)
            context = [c.text for c in earlier if c.start < window[0]]
            romanian = await self._guard(
                job, window, self._translator.translate([c.text for c in own], context)
            )
            if romanian is None:
                return
            cues = [Cue(c.start, c.end, ro) for c, ro in zip(own, romanian, strict=True)]
            self._store.save_span(job.info_hash, job.file_index, window, cues)
            log.info(
                "subtitle_window",
                file=job.file_name,
                start=round(window[0], 1),
                end=round(window[1], 1),
                cues=len(cues),
                seconds=round(self._clock() - t0, 1),
            )
        finally:
            job.in_flight.remove(window)
            self._wake.set()
