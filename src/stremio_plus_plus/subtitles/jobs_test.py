import asyncio
from collections.abc import Callable
from pathlib import Path

import httpx
import numpy as np
import pytest

from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.subtitles import audio
from stremio_plus_plus.subtitles.audio import Audio, AudioTrack
from stremio_plus_plus.subtitles.cues import Cue
from stremio_plus_plus.subtitles.jobs import SubtitleJobs
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.watch.events import FileRequested

IH = "aa" * 20
LENGTH = 1_000_000
DURATION = 600.0  # 5 chunks of 120 s


class FakeStt:
    def __init__(self) -> None:
        self.offsets: list[float] = []

    async def transcribe(self, audio: Audio, offset_s: float) -> list[Cue]:
        self.offsets.append(offset_s)
        base = max(offset_s, 0.0) + (2.0 if offset_s > 0 else 0.0)
        return [Cue(base + 1, base + 2, f"line@{int(base)}")]


class FakeTranslator:
    async def translate(self, lines: list[str], context: list[str]) -> list[str]:
        return [f"ro:{line}" for line in lines]


@pytest.fixture
def fake_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    async def probe(url: str) -> AudioTrack:
        assert url.endswith("?src=companion")
        return AudioTrack(0, True, DURATION)

    async def read_chunk(url: str, track: AudioTrack, start_s: float, length_s: float) -> Audio:
        return np.zeros(16000, np.float32)

    monkeypatch.setattr(audio, "probe", probe)
    monkeypatch.setattr(audio, "read_chunk", read_chunk)


HASH = "1e894d1e08d0e2b7"


def _jobs(tmp_path: Path, stt: FakeStt) -> tuple[SubtitleJobs, SubtitleStore]:
    # Every file of the same length "is" the same video, as the server would hash it.
    opensub = httpx.MockTransport(lambda r: httpx.Response(200, json={"result": {"hash": HASH}}))
    server = StremioServer("http://srv", httpx.AsyncClient(transport=opensub))
    store = SubtitleStore(open_db(tmp_path / "s.db"))
    return SubtitleJobs(server, store, stt, FakeTranslator()), store


async def _until(predicate: Callable[[], bool], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.01)


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_audio")
async def test_resume_mid_file_generates_the_playhead_chunk_first(tmp_path: Path) -> None:
    stt = FakeStt()
    jobs, store = _jobs(tmp_path, stt)
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    # The TV's resume read lands before the file is even probed (the usual order on a resume).
    await jobs(FileRequested(IH, 2, LENGTH // 2))  # 50 % of 600 s → chunk 2
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: len(store.done_chunks(IH, 2)) == 5)
    runner.cancel()
    assert [int(o) for o in stt.offsets] == [238, 358, 478, 118, 0]  # playhead, ahead, back-fill
    assert all(c.text.startswith("ro:") for c in store.cues(IH, 2))


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_audio")
async def test_tail_reads_do_not_move_the_playhead(tmp_path: Path) -> None:
    stt = FakeStt()
    jobs, store = _jobs(tmp_path, stt)
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    await jobs(FileRequested(IH, 2, LENGTH - 10))  # MKV index fetch at the end
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: len(store.done_chunks(IH, 2)) >= 1)
    runner.cancel()
    assert stt.offsets[0] == 0.0


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_audio")
async def test_same_video_from_another_torrent_is_reused_without_generation(tmp_path: Path) -> None:
    stt = FakeStt()
    jobs, store = _jobs(tmp_path, stt)
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: len(store.done_chunks(IH, 2)) == 5)
    calls = len(stt.offsets)
    jobs.ensure("bb" * 20, 0, "Show.S01E03.other.mkv", LENGTH)
    await _until(lambda: len(store.done_chunks("bb" * 20, 0)) == 5)
    runner.cancel()
    assert len(stt.offsets) == calls


@pytest.mark.asyncio
async def test_a_failed_probe_is_retried_when_the_track_is_selected_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A slow torrent: the first probe times out before any data arrives.
    probes: list[str] = []

    async def probe(url: str) -> AudioTrack:
        probes.append(url)
        if len(probes) == 1:
            raise TimeoutError
        return AudioTrack(0, True, DURATION)

    async def read_chunk(url: str, track: AudioTrack, start_s: float, length_s: float) -> Audio:
        return np.zeros(16000, np.float32)

    monkeypatch.setattr(audio, "probe", probe)
    monkeypatch.setattr(audio, "read_chunk", read_chunk)
    now = [1000.0]
    opensub = httpx.MockTransport(lambda r: httpx.Response(200, json={"result": {}}))
    server = StremioServer("http://srv", httpx.AsyncClient(transport=opensub))
    store = SubtitleStore(open_db(tmp_path / "s.db"))
    jobs = SubtitleJobs(server, store, FakeStt(), FakeTranslator(), clock=lambda: now[0])
    runner = asyncio.create_task(jobs.run())
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    await _until(lambda: len(probes) == 1)
    await asyncio.sleep(0.05)
    now[0] += 10  # re-selected right away: still cooling down, no hammering
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    await asyncio.sleep(0.05)
    assert len(probes) == 1
    now[0] += 60  # re-selected a minute later: retried and generated
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    await _until(lambda: len(store.done_chunks(IH, 2)) == 5)
    runner.cancel()
    assert len(probes) == 2
