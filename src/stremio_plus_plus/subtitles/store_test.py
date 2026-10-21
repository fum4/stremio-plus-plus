from pathlib import Path

from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.subtitles.cues import Cue
from stremio_plus_plus.subtitles.store import SubtitleFile, SubtitleStore

IH, OTHER = "aa" * 20, "bb" * 20


def _store(tmp_path: Path) -> SubtitleStore:
    return SubtitleStore(open_db(tmp_path / "state.db"))


def _file(ih: str = IH, video_hash: str | None = "1e894d1e08d0e2b7") -> SubtitleFile:
    return SubtitleFile(ih, 2, "Show.S01E03.mkv", 3560556831, video_hash, 3000.0, 0, True)


def test_spans_persist_and_come_back_in_order(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save_file(_file())
    store.save_span(IH, 2, (112.5, 127.5), [Cue(121.0, 122.0, "Doi")])
    store.save_span(IH, 2, (0.0, 112.5), [Cue(1.0, 2.0, "Unu"), Cue(3.0, 4.0, "Ăștia ț")])
    assert sorted(store.spans(IH, 2)) == [(0.0, 112.5), (112.5, 127.5)]
    assert [c.text for c in store.cues(IH, 2)] == ["Unu", "Ăștia ț", "Doi"]


def test_same_video_in_another_torrent_reuses_spans(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save_file(_file())
    store.save_span(IH, 2, (0.0, 15.0), [Cue(1.0, 2.0, "Unu")])
    source = store.find_same_video("1e894d1e08d0e2b7", 3560556831)
    assert source is not None
    store.save_file(_file(OTHER))
    store.copy_spans(source, OTHER, 2)
    assert [c.text for c in store.cues(OTHER, 2)] == ["Unu"]
    assert store.find_same_video("ffff", 1) is None


def test_chunks_from_before_spans_carry_over(tmp_path: Path) -> None:
    db = open_db(tmp_path / "state.db")
    db.execute(
        "INSERT INTO subtitle_chunks VALUES (?, 2, 1, '[[121.0, 122.0, \"Doi\"]]', 0)", (IH,)
    )
    db.execute(
        "INSERT INTO subtitle_spans SELECT info_hash, file_index, chunk_index * 120.0,"
        " (chunk_index + 1) * 120.0, cues_json, created_at FROM subtitle_chunks"
    )  # what migration 3 does to chunks generated before it
    store = SubtitleStore(db)
    assert store.spans(IH, 2) == [(120.0, 240.0)]
    assert [c.text for c in store.cues(IH, 2)] == ["Doi"]
