"""When the TV last played each file — drives the 7-day cleanup and resume detection."""

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class FilePlay:
    info_hash: str
    file_index: int
    file_name: str
    file_length: int
    last_offset: int
    last_played_at: float


class Plays:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(self, play: FilePlay) -> None:
        self._conn.execute(
            """
            INSERT INTO file_plays VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (info_hash, file_index) DO UPDATE SET
                file_name = excluded.file_name, file_length = excluded.file_length,
                last_offset = excluded.last_offset, last_played_at = excluded.last_played_at
            """,
            (
                play.info_hash,
                play.file_index,
                play.file_name,
                play.file_length,
                play.last_offset,
                play.last_played_at,
                play.last_played_at,
            ),
        )

    def get(self, info_hash: str, file_index: int) -> FilePlay | None:
        row = self._conn.execute(
            "SELECT * FROM file_plays WHERE info_hash = ? AND file_index = ?",
            (info_hash, file_index),
        ).fetchone()
        return _row(row) if row else None

    def last_played_per_torrent(self) -> dict[str, float]:
        rows = self._conn.execute(
            "SELECT info_hash, MAX(last_played_at) AS at FROM file_plays GROUP BY info_hash"
        ).fetchall()
        return {r["info_hash"]: float(r["at"]) for r in rows}

    def played_before(self, cutoff: float) -> list[FilePlay]:
        rows = self._conn.execute(
            "SELECT * FROM file_plays WHERE last_played_at < ? ORDER BY last_played_at", (cutoff,)
        ).fetchall()
        return [_row(r) for r in rows]

    def forget_torrent(self, info_hash: str) -> None:
        self._conn.execute("DELETE FROM file_plays WHERE info_hash = ?", (info_hash,))

    def forget(self, info_hash: str, file_index: int) -> None:
        self._conn.execute(
            "DELETE FROM file_plays WHERE info_hash = ? AND file_index = ?", (info_hash, file_index)
        )


def _row(row: sqlite3.Row) -> FilePlay:
    return FilePlay(
        info_hash=row["info_hash"],
        file_index=row["file_index"],
        file_name=row["file_name"],
        file_length=row["file_length"],
        last_offset=row["last_offset"],
        last_played_at=row["last_played_at"],
    )
