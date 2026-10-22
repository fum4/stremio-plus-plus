"""One ffmpeg process cutting a source into MPEG-TS segments from segment `first` onwards.

Video is copied, so ffmpeg can only cut on keyframes: `-segment_times` lists the nominal
boundaries and every cut lands on the first keyframe at or after one. Those times are relative
to the first packet written, which (an input seek with stream copy) is the keyframe at or before
the start, so a restart at segment j cuts every later segment exactly where a run from the
beginning would have. `-copyts` + TS_OFFSET_S keep timestamps those of the source, so segments
from different runs line up and the subtitle timestamp map never changes.
"""

import asyncio
import contextlib
import math
import os
import signal
import subprocess
from pathlib import Path

import structlog

from stremio_plus_plus.stream.constants import (
    SEGMENT_S,
    STOP_TIMEOUT_S,
    SYSTEM_B_AUDIO,
    TS_OFFSET_S,
)
from stremio_plus_plus.stream.media import PROTOCOLS, Media, keyframe_at

log = structlog.get_logger()


def segment_count(duration_s: float) -> int:
    return max(1, math.ceil(duration_s / SEGMENT_S))


def segment_path(directory: Path, index: int) -> Path:
    return directory / f"{index:05d}.ts"


def cut_times(media: Media, first: int, first_packet_s: float) -> list[float]:
    """Nominal boundaries after segment `first`, relative to the first packet written."""
    origin = first_packet_s - media.start_s
    return [
        index * SEGMENT_S - origin for index in range(first + 1, segment_count(media.duration_s))
    ]


def command(url: str, media: Media, first: int, times: list[float], out: Path) -> list[str]:
    ts_options = "mpegts_copyts=1"
    if media.audio_codec in SYSTEM_B_AUDIO:
        ts_options += ":mpegts_flags=system_b"
    seek = ["-ss", f"{first * SEGMENT_S:.3f}"] if first else []
    return [
        "ffmpeg", *PROTOCOLS, "-v", "error", "-nostdin", *seek, "-copyts", "-i", url,
        "-map", "0:v:0", "-map", f"0:a:{media.audio_index}",
        "-c:v", "copy", *(["-tag:v", "hvc1"] if media.video_codec == "hevc" else []),
        *media.audio_args,
        "-f", "segment", "-segment_format", "mpegts", "-segment_format_options", ts_options,
        "-segment_start_number", str(first),
        *(["-segment_times", ",".join(f"{t:.3f}" for t in times)] if times else []),
        "-output_ts_offset", str(TS_OFFSET_S), "-muxdelay", "0", "-muxpreload", "0",
        str(out / "%05d.ts"),
    ]  # fmt: skip


class Producer:
    def __init__(self, url: str, media: Media, directory: Path, first: int) -> None:
        self.url = url
        self.media = media
        self.dir = directory
        self.first = first
        self.total = segment_count(media.duration_s)
        self.kept_from = first  # segments before this were deleted
        self._head = first
        self.started_at = 0.0
        self._proc: subprocess.Popen[bytes] | None = None
        self._paused = False

    async def start(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        packet = await keyframe_at(self.url, self.media.start_s + self.first * SEGMENT_S)
        times = cut_times(self.media, self.first, packet)
        argv = command(self.url, self.media, self.first, times, self.dir)
        # A plain Popen, polled with WNOHANG: asyncio's child watcher on macOS blocks the event
        # loop in waitpid() once the child is SIGSTOPped (pause()), freezing the whole app.
        # stderr discarded: ffmpeg's errors quote the input URL, and debrid links are secrets.
        self._proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("stream_producer_started", first=self.first, total=self.total)

    @property
    def done(self) -> bool:
        return self._proc is not None and self._proc.poll() is not None

    @property
    def failed(self) -> bool:
        return self.done and self._proc is not None and self._proc.poll() != 0

    @property
    def returncode(self) -> int | None:
        return self._proc.poll() if self._proc is not None else None

    def head(self) -> int:
        """Index of the segment being written now (the newest file present)."""
        while self._head + 1 < self.total and segment_path(self.dir, self._head + 1).exists():
            self._head += 1
        return self._head

    def finished(self, index: int) -> bool:
        """Segment `index` is complete: the next one has started, or ffmpeg ended cleanly."""
        if index < self.kept_from or not segment_path(self.dir, index).exists():
            return False
        if index + 1 < self.total and segment_path(self.dir, index + 1).exists():
            return True
        return self.done and not self.failed

    def forget_before(self, index: int) -> None:
        self.head()  # advance past them first: head() walks forward over existing files
        for stale in range(self.kept_from, min(index, self._head)):
            segment_path(self.dir, stale).unlink(missing_ok=True)
        self.kept_from = max(self.kept_from, min(index, self._head))

    def pause(self, paused: bool) -> None:
        if self._proc is None or self.done or paused == self._paused:
            return
        os.kill(self._proc.pid, signal.SIGSTOP if paused else signal.SIGCONT)
        self._paused = paused

    async def stop(self) -> None:
        if self._proc is None or self.done:
            return
        with contextlib.suppress(ProcessLookupError):
            self.pause(False)  # a stopped process can't act on SIGTERM
            self._proc.terminate()
        try:
            await asyncio.to_thread(self._proc.wait, STOP_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                self._proc.kill()
            await asyncio.to_thread(self._proc.wait)
