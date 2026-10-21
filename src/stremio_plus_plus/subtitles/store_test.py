from pathlib import Path

from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.subtitles.cues import Cue
from stremio_plus_plus.subtitles.store import SubtitleFile, SubtitleStore

IH, OTHER = "aa" * 20, "bb" * 20


def _store(tmp_path: Path) -> SubtitleStore:
    return SubtitleStore(open_db(tmp_path / "state.db"))


def _file(ih: str = IH, video_hash: str | None = "1e894d1e08d0e2b7") -> SubtitleFile:
    return SubtitleFile(ih, 2, "Show.S01E03.mkv", 3560556831, video_hash, 3000.0, 0, True)


def test_chunks_persist_and_come_back_in_order(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save_file(_file())
    store.save_chunk(IH, 2, 1, [Cue(121.0, 122.0, "Doi")])
    store.save_chunk(IH, 2, 0, [Cue(1.0, 2.0, "Unu"), Cue(3.0, 4.0, "Ăștia ț")])
    assert store.done_chunks(IH, 2) == {0, 1}
    assert [c.text for c in store.cues(IH, 2)] == ["Unu", "Ăștia ț", "Doi"]


def test_same_video_in_another_torrent_reuses_chunks(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save_file(_file())
    store.save_chunk(IH, 2, 0, [Cue(1.0, 2.0, "Unu")])
    source = store.find_same_video("1e894d1e08d0e2b7", 3560556831)
    assert source is not None
    store.save_file(_file(OTHER))
    store.copy_chunks(source, OTHER, 2)
    assert [c.text for c in store.cues(OTHER, 2)] == ["Unu"]
    assert store.find_same_video("ffff", 1) is None
