import pytest

from stremio_plus_plus.subtitles import audio
from stremio_plus_plus.subtitles.audio import AudioTrack, choose_track


def test_prefers_english_default_and_skips_commentary() -> None:
    probe = {
        "format": {"duration": "3012.5"},
        "streams": [
            {"channels": 2, "tags": {"language": "ita"}, "disposition": {"default": 1}},
            {"channels": 2, "tags": {"language": "eng", "title": "Director's commentary"}},
            {"channels": 6, "channel_layout": "5.1(side)", "tags": {"language": "eng"}},
        ],
    }
    track = choose_track(probe)
    assert track is not None
    assert (track.stream, track.center, track.duration_s) == (2, True, 3012.5)


def test_stereo_track_is_downmixed_not_centre() -> None:
    track = choose_track({"streams": [{"channels": 2, "channel_layout": "stereo"}]})
    assert track is not None and track.center is False


def test_no_audio() -> None:
    assert choose_track({"streams": []}) is None


@pytest.mark.asyncio
async def test_ffmpeg_and_ffprobe_only_speak_http(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    async def fake_run(*argv: str, timeout_s: float) -> bytes:
        calls.append(argv)
        return b"{}"

    monkeypatch.setattr(audio, "_run", fake_run)
    await audio.probe("http://srv/x?src=companion")
    await audio.read_chunk("http://srv/x?src=companion", AudioTrack(0, True, 10.0), 0.0, 1.0)
    for argv in calls:
        whitelist = argv.index("-protocol_whitelist")
        assert argv[whitelist + 1] == "http,tcp"
        if "-i" in argv:
            assert whitelist < argv.index("-i")
