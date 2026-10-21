"""Every generated subtitle chunk, kept forever (a 50-min episode is ~40 KB): a rewatch or a resume
is served from here instead of regenerating."""

import json
import sqlite3
import time
from dataclasses import dataclass

from stremio_plus_plus.subtitles.cues import Cue


@dataclass(frozen=True)
class SubtitleFile:
    info_hash: str
    file_index: int
    file_name: str
    file_length: int
    video_hash: str | None
    duration_s: float
    audio_stream: int
    center: bool


class SubtitleStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save_file(self, f: SubtitleFile) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO subtitle_files VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f.info_hash,
                f.file_index,
                f.file_name,
                f.file_length,
                f.video_hash,
                f.duration_s,
                f.audio_stream,
                int(f.center),
            ),
        )

    def set_video_hash(self, info_hash: str, file_index: int, video_hash: str) -> None:
        self._conn.execute(
            "UPDATE subtitle_files SET video_hash = ? WHERE info_hash = ? AND file_index = ?",
            (video_hash, info_hash, file_index),
        )

    def file(self, info_hash: str, file_index: int) -> SubtitleFile | None:
        row = self._conn.execute(
            "SELECT * FROM subtitle_files WHERE info_hash = ? AND file_index = ?",
            (info_hash, file_index),
        ).fetchone()
        return _file(row) if row else None

    def find_same_video(self, video_hash: str, file_length: int) -> SubtitleFile | None:
        """The same video seen in another torrent (OpenSubtitles hash + size match)."""
        row = self._conn.execute(
            "SELECT * FROM subtitle_files WHERE video_hash = ? AND file_length = ? LIMIT 1",
            (video_hash, file_length),
        ).fetchone()
        return _file(row) if row else None

    def done_chunks(self, info_hash: str, file_index: int) -> set[int]:
        rows = self._conn.execute(
            "SELECT chunk_index FROM subtitle_chunks WHERE info_hash = ? AND file_index = ?",
            (info_hash, file_index),
        ).fetchall()
        return {int(r[0]) for r in rows}

    def save_chunk(
        self, info_hash: str, file_index: int, chunk_index: int, cues: list[Cue]
    ) -> None:
        payload = json.dumps([[c.start, c.end, c.text] for c in cues], ensure_ascii=False)
        self._conn.execute(
            "INSERT OR REPLACE INTO subtitle_chunks VALUES (?, ?, ?, ?, ?)",
            (info_hash, file_index, chunk_index, payload, time.time()),
        )

    def cues(self, info_hash: str, file_index: int) -> list[Cue]:
        rows = self._conn.execute(
            "SELECT cues_json FROM subtitle_chunks WHERE info_hash = ? AND file_index = ?"
            " ORDER BY chunk_index",
            (info_hash, file_index),
        ).fetchall()
        return [
            Cue(float(s), float(e), str(t))
            for (payload,) in rows
            for s, e, t in json.loads(payload)
        ]

    def copy_chunks(self, source: SubtitleFile, info_hash: str, file_index: int) -> None:
        self._conn.execute(
            """INSERT OR IGNORE INTO subtitle_chunks
               SELECT ?, ?, chunk_index, cues_json, created_at FROM subtitle_chunks
               WHERE info_hash = ? AND file_index = ?""",
            (info_hash, file_index, source.info_hash, source.file_index),
        )


def _file(row: sqlite3.Row) -> SubtitleFile:
    return SubtitleFile(
        info_hash=row["info_hash"],
        file_index=row["file_index"],
        file_name=row["file_name"],
        file_length=row["file_length"],
        video_hash=row["video_hash"],
        duration_s=row["duration_s"],
        audio_stream=row["audio_stream"],
        center=bool(row["center"]),
    )
