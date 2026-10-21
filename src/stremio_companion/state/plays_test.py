from pathlib import Path

from stremio_companion.state.db import MIGRATIONS, open_db
from stremio_companion.state.plays import FilePlay, Plays

IH = "aa" * 20


def _play(idx: int, at: float, offset: int = 0) -> FilePlay:
    return FilePlay(IH, idx, f"Show.S01E0{idx + 1}.mkv", 1000, offset, at)


def test_record_upserts_and_keeps_latest(tmp_path: Path) -> None:
    plays = Plays(open_db(tmp_path / "state.db"))
    plays.record(_play(0, 100.0))
    plays.record(_play(0, 200.0, offset=500))
    got = plays.get(IH, 0)
    assert got is not None and got.last_played_at == 200.0 and got.last_offset == 500


def test_played_before_and_forget(tmp_path: Path) -> None:
    plays = Plays(open_db(tmp_path / "state.db"))
    plays.record(_play(0, 100.0))
    plays.record(_play(1, 300.0))
    assert [p.file_index for p in plays.played_before(200.0)] == [0]
    assert plays.last_played_per_torrent() == {IH: 300.0}
    plays.forget(IH, 0)
    assert plays.get(IH, 0) is None


def test_migrations_are_idempotent_across_reopen(tmp_path: Path) -> None:
    open_db(tmp_path / "state.db").close()
    conn = open_db(tmp_path / "state.db")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(MIGRATIONS)


def test_forget_torrent(tmp_path: Path) -> None:
    plays = Plays(open_db(tmp_path / "state.db"))
    plays.record(_play(0, 1.0))
    plays.record(_play(1, 2.0))
    plays.forget_torrent(IH)
    assert plays.last_played_per_torrent() == {}
