"""SQLite state (stdlib): one file in COMPANION_DATA_DIR, migrated via PRAGMA user_version."""

import sqlite3
from pathlib import Path

# Append-only: each entry migrates from version i to i+1. Never edit a shipped entry.
MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE file_plays (
        info_hash       TEXT    NOT NULL,
        file_index      INTEGER NOT NULL,
        file_name       TEXT    NOT NULL,
        file_length     INTEGER NOT NULL,
        last_offset     INTEGER NOT NULL,
        first_played_at REAL    NOT NULL,
        last_played_at  REAL    NOT NULL,
        PRIMARY KEY (info_hash, file_index)
    );
    """,
    """
    CREATE TABLE subtitle_files (
        info_hash     TEXT    NOT NULL,
        file_index    INTEGER NOT NULL,
        file_name     TEXT    NOT NULL,
        file_length   INTEGER NOT NULL,
        video_hash    TEXT,
        duration_s    REAL    NOT NULL,
        audio_stream  INTEGER NOT NULL,
        center        INTEGER NOT NULL,
        PRIMARY KEY (info_hash, file_index)
    );
    CREATE INDEX subtitle_files_by_video ON subtitle_files (video_hash, file_length);
    CREATE TABLE subtitle_chunks (
        info_hash   TEXT    NOT NULL,
        file_index  INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        cues_json   TEXT    NOT NULL,
        created_at  REAL    NOT NULL,
        PRIMARY KEY (info_hash, file_index, chunk_index)
    );
    """,
    # Subtitles generated in windows of any length (subtitles/scheduler.py); the fixed 120 s
    # chunks carry over as spans. subtitle_chunks stays, unused (append-only migrations).
    """
    CREATE TABLE subtitle_spans (
        info_hash   TEXT    NOT NULL,
        file_index  INTEGER NOT NULL,
        start_s     REAL    NOT NULL,
        end_s       REAL    NOT NULL,
        cues_json   TEXT    NOT NULL,
        created_at  REAL    NOT NULL,
        PRIMARY KEY (info_hash, file_index, start_s)
    );
    INSERT INTO subtitle_spans
        SELECT info_hash, file_index, chunk_index * 120.0, (chunk_index + 1) * 120.0,
               cues_json, created_at
        FROM subtitle_chunks;
    """,
    """
    CREATE TABLE activity (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        ts            REAL    NOT NULL,
        updated       REAL    NOT NULL,
        category      TEXT    NOT NULL,
        kind          TEXT    NOT NULL,
        title         TEXT    NOT NULL,
        detail        TEXT,
        image         TEXT,
        coalesce_key  TEXT,
        count         INTEGER NOT NULL DEFAULT 1
    );
    CREATE INDEX activity_by_updated ON activity (updated);
    CREATE INDEX activity_by_key ON activity (coalesce_key, updated);
    """,
)


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    for i, sql in enumerate(MIGRATIONS[version:], start=version + 1):
        conn.executescript(f"BEGIN; {sql} PRAGMA user_version={i}; COMMIT;")
    return conn
