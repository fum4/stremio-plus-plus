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
