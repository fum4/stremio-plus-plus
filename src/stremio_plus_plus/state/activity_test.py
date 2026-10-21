from pathlib import Path

from stremio_plus_plus.state.activity import ActivityStore
from stremio_plus_plus.state.db import open_db


def test_coalesces_within_the_window_then_starts_a_new_row(tmp_path: Path) -> None:
    now = [1000.0]
    store = ActivityStore(open_db(tmp_path / "s.db"), clock=lambda: now[0])
    first = store.add("subtitles", "window", "1 window", key="subs:a", within_s=60)
    now[0] += 30
    again = store.add("subtitles", "window", "2 windows", key="subs:a", within_s=60)
    now[0] += 120
    later = store.add("subtitles", "window", "1 window", key="subs:a", within_s=60)
    assert first == again != later
    rows = store.changed_since(0, 10)
    assert [(r.title, r.count) for r in rows] == [("1 window", 1), ("2 windows", 2)]
    assert store.changed_since(1031, 10)[0].id == later
    assert [r.id for r in store.before(later, 10)] == [first]
