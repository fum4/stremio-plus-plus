from dataclasses import replace
from pathlib import Path

from stremio_plus_plus.stream.playlists_test import MEDIA
from stremio_plus_plus.stream.producer import command, cut_times, segment_count

LONG = replace(MEDIA, duration_s=40.0)


def test_cut_times_are_relative_to_the_keyframe_a_restart_lands_on() -> None:
    # Restart at segment 3 (18 s): the input seek lands on the keyframe at 16.4 s.
    assert cut_times(LONG, 3, 16.4) == [24 - 16.4, 30 - 16.4, 36 - 16.4]
    assert segment_count(40.0) == 7


def test_eac3_gets_dvb_signalling_and_timestamps_are_kept() -> None:
    argv = command("http://srv/x", LONG, 3, [7.6], Path("/tmp/out"))
    joined = " ".join(argv)
    assert "-ss 18.000" in joined and "-copyts" in joined
    assert "mpegts_copyts=1:mpegts_flags=system_b" in joined
    assert "-segment_start_number 3" in joined and "-c:v copy" in joined


def test_dolby_digital_keeps_the_default_signalling() -> None:
    ac3 = replace(LONG, audio_codec="ac3")
    assert "system_b" not in " ".join(command("u", ac3, 0, [], Path("/o")))
