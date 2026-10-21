from stremio_companion.subtitles.audio import choose_track


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
