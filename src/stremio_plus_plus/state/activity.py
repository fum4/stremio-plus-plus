"""The activity feed's history (SQLite): what happened, in plain words, kept across restarts.

Repeated happenings coalesce into one row (same key within a window: "14 subtitle windows")
instead of flooding the feed.
"""

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

Category = Literal["playback", "subtitles", "downloads", "system", "problem"]
KEEP_ROWS = 5000


@dataclass(frozen=True)
class Activity:
    id: int
    ts: float
    updated: float
    category: Category
    kind: str
    title: str
    detail: str | None
    image: str | None
    count: int


class ActivityStore:
    def __init__(self, conn: sqlite3.Connection, clock: Callable[[], float] = time.time) -> None:
        self._conn = conn
        self._clock = clock

    def add(
        self,
        category: Category,
        kind: str,
        title: str,
        detail: str | None = None,
        image: str | None = None,
        *,
        key: str | None = None,
        within_s: float = 0.0,
        at: float | None = None,  # when it happened, if not now (backfill from the log history)
    ) -> int:
        """A new row, or (same `key` updated within `within_s`) that row bumped and rewritten."""
        now = at if at is not None else self._clock()
        if key is not None and within_s > 0:
            row = self._conn.execute(
                "SELECT id FROM activity WHERE coalesce_key = ? AND updated >= ?"
                " ORDER BY updated DESC LIMIT 1",
                (key, now - within_s),
            ).fetchone()
            if row is not None:
                self._conn.execute(
                    "UPDATE activity SET updated = ?, title = ?, detail = ?,"
                    " image = COALESCE(?, image), count = count + 1 WHERE id = ?",
                    (now, title, detail, image, row["id"]),
                )
                return int(row["id"])
        cur = self._conn.execute(
            "INSERT INTO activity (ts, updated, category, kind, title, detail, image, coalesce_key)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now, now, category, kind, title, detail, image, key),
        )
        if (cur.lastrowid or 0) % 200 == 0:
            self._conn.execute(
                "DELETE FROM activity WHERE id <= (SELECT MAX(id) FROM activity) - ?", (KEEP_ROWS,)
            )
        return int(cur.lastrowid or 0)

    def empty(self) -> bool:
        return self._conn.execute("SELECT 1 FROM activity LIMIT 1").fetchone() is None

    def changed_since(self, updated: float, limit: int) -> list[Activity]:
        rows = self._conn.execute(
            "SELECT * FROM activity WHERE updated > ? ORDER BY updated DESC LIMIT ?",
            (updated, limit),
        ).fetchall()
        return [_activity(r) for r in rows]

    def before(self, id_: int, limit: int) -> list[Activity]:
        rows = self._conn.execute(
            "SELECT * FROM activity WHERE id < ? ORDER BY id DESC LIMIT ?", (id_, limit)
        ).fetchall()
        return [_activity(r) for r in rows]


def _activity(row: sqlite3.Row) -> Activity:
    return Activity(
        id=row["id"],
        ts=row["ts"],
        updated=row["updated"],
        category=row["category"],
        kind=row["kind"],
        title=row["title"],
        detail=row["detail"],
        image=row["image"],
        count=row["count"],
    )
