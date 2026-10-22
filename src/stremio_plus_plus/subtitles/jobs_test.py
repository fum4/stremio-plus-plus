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
from stremio_plus_plus.subtitles.scheduler import Span, merged
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.watch.events import FileRequested

IH = "aa" * 20
LENGTH = 1_000_000
DURATION = 600.0


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


def _complete(store: SubtitleStore, ih: str = IH, index: int = 2) -> bool:
    spans = merged(store.spans(ih, index))
    return len(spans) == 1 and spans[0][0] == 0.0 and spans[0][1] >= DURATION


async def _until(predicate: Callable[[], bool], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.01)


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_audio")
async def test_resume_mid_file_starts_ahead_of_the_playhead_then_covers_everything(
    tmp_path: Path,
) -> None:
    stt = FakeStt()
    jobs, store = _jobs(tmp_path, stt)
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    jobs.want(IH, 2)
    # The TV's resume read lands before the file is even probed (the usual order on a resume).
    await jobs(FileRequested(IH, 2, LENGTH // 2))  # 50 % of 600 s → 300 s
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: _complete(store))
    runner.cancel()
    # First window aimed where the viewer will be (300 + 12.5 s), read with 2 s overlap.
    assert stt.offsets[0] == 310.5
    ahead = [o for o in stt.offsets if o >= 310.5]
    assert ahead == sorted(ahead)  # forward from the playhead before any back-fill
    assert all(c.text.startswith("ro:") for c in store.cues(IH, 2))


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_audio")
async def test_tail_reads_do_not_move_the_playhead(tmp_path: Path) -> None:
    stt = FakeStt()
    jobs, store = _jobs(tmp_path, stt)
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    jobs.want(IH, 2)
    await jobs(FileRequested(IH, 2, LENGTH - 10))  # MKV index fetch at the end
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: bool(store.spans(IH, 2)))
    runner.cancel()
    assert stt.offsets[0] == 10.5  # from the start (12.5 s ahead of 0), not the end


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_audio")
async def test_same_video_from_another_torrent_is_reused_without_generation(tmp_path: Path) -> None:
    stt = FakeStt()
    jobs, store = _jobs(tmp_path, stt)
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    jobs.want(IH, 2)
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: _complete(store))
    calls = len(stt.offsets)
    jobs.ensure("bb" * 20, 0, "Show.S01E03.other.mkv", LENGTH)
    jobs.want("bb" * 20, 0)
    await _until(lambda: _complete(store, "bb" * 20, 0))
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
    jobs.want(IH, 2)
    await _until(lambda: len(probes) == 1)
    await asyncio.sleep(0.05)
    now[0] += 10  # re-selected right away: still cooling down, no hammering
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    jobs.want(IH, 2)
    await asyncio.sleep(0.05)
    assert len(probes) == 1
    now[0] += 60  # re-selected a minute later: retried and generated
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    jobs.want(IH, 2)
    await _until(lambda: _complete(store))
    runner.cancel()
    assert len(probes) == 2


@pytest.mark.asyncio
async def test_the_first_window_is_served_while_the_rest_is_still_downloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    later = asyncio.Event()  # the torrent is slow: audio past the first window isn't there yet

    async def probe(url: str) -> AudioTrack:
        return AudioTrack(0, True, DURATION)

    async def read_chunk(url: str, track: AudioTrack, start_s: float, length_s: float) -> Audio:
        if start_s > 20:
            await later.wait()
        return np.zeros(16000, np.float32)

    monkeypatch.setattr(audio, "probe", probe)
    monkeypatch.setattr(audio, "read_chunk", read_chunk)
    jobs, store = _jobs(tmp_path, FakeStt())
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    jobs.want(IH, 2)
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: bool(jobs.cues(IH, 2)))
    assert store.spans(IH, 2) == [(12.5, 27.5)]
    later.set()
    await _until(lambda: _complete(store))
    runner.cancel()


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_audio")
async def test_the_next_window_is_transcribed_while_the_previous_is_translated(
    tmp_path: Path,
) -> None:
    stt = FakeStt()

    class WaitsForNextTranscription(FakeTranslator):
        async def translate(self, lines: list[str], context: list[str]) -> list[str]:
            # Only finishes once Whisper has moved on: deadlocks if the steps ran one by one.
            await _until(lambda: len(stt.offsets) >= 2 or _complete(store))
            return await super().translate(lines, context)

    opensub = httpx.MockTransport(lambda r: httpx.Response(200, json={"result": {}}))
    server = StremioServer("http://srv", httpx.AsyncClient(transport=opensub))
    store = SubtitleStore(open_db(tmp_path / "s.db"))
    jobs = SubtitleJobs(server, store, stt, WaitsForNextTranscription())
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    jobs.want(IH, 2)
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: len(store.spans(IH, 2)) >= 1)
    runner.cancel()
    assert len(stt.offsets) >= 2


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_audio")
async def test_the_next_episode_is_generated_whole_after_the_playing_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs, store = _jobs(tmp_path, FakeStt())
    saved: list[tuple[int, float]] = []
    save = store.save_span

    def recording(ih: str, index: int, span: Span, cues: list[Cue]) -> None:
        saved.append((index, span[0]))
        save(ih, index, span, cues)

    monkeypatch.setattr(store, "save_span", recording)
    jobs.prepare_next(IH, 2, 3, "Show.S01E04.mkv", LENGTH)  # E03 has no subtitle job: ignored
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    jobs.want(IH, 2)
    jobs.prepare_next(IH, 2, 3, "Show.S01E04.mkv", LENGTH)
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: _complete(store, IH, 3))
    runner.cancel()
    order = [i for i, _ in saved]
    assert order == sorted(order)  # every E03 window before any E04 one
    assert next(start for i, start in saved if i == 3) == 0.0  # E04 from 0:00, not aimed ahead


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_audio")
async def test_until_the_track_is_picked_only_the_start_is_generated(tmp_path: Path) -> None:
    stt = FakeStt()
    jobs, store = _jobs(tmp_path, stt)
    jobs.ensure(IH, 2, "Show.S01E03.mkv", LENGTH)
    runner = asyncio.create_task(jobs.run())
    await _until(lambda: bool(store.spans(IH, 2)) and not jobs._jobs[(IH, 2)].in_flight)  # pyright: ignore[reportPrivateUsage]
    await asyncio.sleep(0.05)
    assert max(end for _, end in store.spans(IH, 2)) <= 120.0 + 120.0  # PRIME_S + one window
    assert not _complete(store)
    jobs.want(IH, 2)
    await _until(lambda: _complete(store))
    runner.cancel()
