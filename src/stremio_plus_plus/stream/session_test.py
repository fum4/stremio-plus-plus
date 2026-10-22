from pathlib import Path

from stremio_plus_plus.stream.session import Session, Source

SOURCE = Source("k", "http://srv/x", "aa" * 20, 0, "x.mkv", 1000)


def test_subtitle_runs_restart_on_a_seek(tmp_path: Path) -> None:
    session = Session(SOURCE, tmp_path)
    for index in (0, 1, 2, 2, 3):  # a repeat is not a jump
        session.served_vtt(index)
    assert (session.vtt_run_start, session.vtt_served_until) == (0.0, 24.0)
    session.served_vtt(400)  # seek: the bridge must not cover 0-24 s again
    assert (session.vtt_run_start, session.vtt_served_until) == (2400.0, 2406.0)
    session.served_vtt(401)
    assert session.vtt_served_until == 2412.0
