"""Generates Romanian subtitles chunk by chunk for the files the TV plays, playhead first."""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import structlog

from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.subtitles import audio
from stremio_plus_plus.subtitles.constants import (
    CHUNK_S,
    MAX_CHUNK_FAILURES,
    OVERLAP_S,
    TAIL_READ_FRACTION,
)
from stremio_plus_plus.subtitles.cues import Cue
from stremio_plus_plus.subtitles.scheduler import chunk_count, next_chunk
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
    failures: dict[int, int] = field(default_factory=dict[int, int])
    dead: bool = False


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
        job.last_active = self._clock()
        self._wake.set()

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
        while True:
            job, chunk = self._pick()
            if job is None:
                self._wake.clear()
                await self._wake.wait()
                continue
            try:
                if job.meta is None:
                    await self._prepare(job)
                elif chunk is not None:
                    await self._generate(job, chunk)
            except Exception:  # one bad chunk or file must not stop subtitles for everything else
                log.exception("subtitle_chunk_failed", file=job.file_name, chunk=chunk)
                if chunk is None:
                    job.dead = True
                else:
                    job.failures[chunk] = job.failures.get(chunk, 0) + 1

    def _pick(self) -> tuple[_Job | None, int | None]:
        for job in sorted(self._jobs.values(), key=lambda j: j.last_active, reverse=True):
            if job.dead:
                continue
            if job.meta is None:
                return job, None
            done = self._store.done_chunks(job.info_hash, job.file_index)
            skipped = {i for i, n in job.failures.items() if n >= MAX_CHUNK_FAILURES}
            total = chunk_count(job.meta.duration_s, CHUNK_S)
            playhead_s = job.playhead_fraction * job.meta.duration_s
            chunk = next_chunk(done | skipped, total, int(playhead_s // CHUNK_S))
            if chunk is not None:
                return job, chunk
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
            self._store.copy_chunks(same, job.info_hash, job.file_index)
            log.info("subtitles_reused_from_same_video", file=job.file_name)
            return
        track = await audio.probe(self._server.file_url(job.info_hash, job.file_index))
        if track is None:
            job.dead = True
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

    async def _generate(self, job: _Job, chunk: int) -> None:
        assert job.meta is not None
        t0 = self._clock()
        window_start = max(0.0, chunk * CHUNK_S - OVERLAP_S)
        track = audio.AudioTrack(job.meta.audio_stream, job.meta.center, job.meta.duration_s)
        samples = await audio.read_chunk(
            self._server.file_url(job.info_hash, job.file_index),
            track,
            window_start,
            CHUNK_S + OVERLAP_S,
        )
        heard = await self._stt.transcribe(samples, window_start)
        own = [c for c in heard if chunk * CHUNK_S <= c.start < (chunk + 1) * CHUNK_S]
        context = [
            c.text
            for c in self._store.cues(job.info_hash, job.file_index)
            if c.start < chunk * CHUNK_S
        ]
        romanian = await self._translator.translate([c.text for c in own], context)
        self._store.save_chunk(
            job.info_hash,
            job.file_index,
            chunk,
            [Cue(c.start, c.end, ro) for c, ro in zip(own, romanian, strict=True)],
        )
        log.info(
            "subtitle_chunk",
            file=job.file_name,
            chunk=chunk,
            cues=len(own),
            seconds=round(self._clock() - t0, 1),
        )
