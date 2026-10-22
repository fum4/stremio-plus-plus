from typing import Any

import pytest

from stremio_plus_plus.stream.media import UnsupportedMediaError, plan


def _probe(audio: list[dict[str, Any]], video: str = "hevc") -> dict[str, Any]:
    streams: list[dict[str, Any]] = [
        {"codec_type": "video", "codec_name": video, "profile": "Main 10", "level": 150,
         "width": 3840, "height": 1604},
        *({"codec_type": "audio", **a} for a in audio),
    ]  # fmt: skip
    return {"streams": streams, "format": {"duration": "2833.7", "start_time": "0.000"}}


def test_audio_the_tv_plays_in_hls_is_copied() -> None:
    media = plan(_probe([{"codec_name": "eac3", "channels": 6}]))
    assert media.audio_args == ("-c:a", "copy")
    assert (media.audio_tag, media.video_tag) == ("ec-3", "hvc1.2.4.L150.B0")


def test_dts_becomes_dolby_digital_51() -> None:
    media = plan(_probe([{"codec_name": "dts", "channels": 8}]))
    assert media.audio_codec == "ac3"
    assert media.audio_args == ("-c:a", "ac3", "-b:a", "640k", "-ac", "6")


def test_english_main_track_beats_commentary() -> None:
    media = plan(
        _probe(
            [
                {"codec_name": "aac", "tags": {"language": "eng", "title": "Commentary"}},
                {"codec_name": "aac", "tags": {"language": "ita"}},
                {"codec_name": "ac3", "tags": {"language": "eng"}},
            ]
        )
    )
    assert media.audio_index == 2


def test_codecs_the_tv_cannot_take_are_refused() -> None:
    with pytest.raises(UnsupportedMediaError):
        plan(_probe([{"codec_name": "aac"}], video="av1"))
