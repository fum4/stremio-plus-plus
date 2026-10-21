import asyncio
from pathlib import Path

import httpx
import pytest

from stremio_plus_plus.app.activity import ActivityFeed
from stremio_plus_plus.app.activity_rules import pretty_name
from stremio_plus_plus.log.hub import LogHub
from stremio_plus_plus.meta.cinemeta import Cinemeta
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.activity import ActivityStore
from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.subtitles.store import SubtitleFile, SubtitleStore
from stremio_plus_plus.watch.events import ClientSeen, FileRequested

IH = "ab" * 20
GB = 1024**3
STATS = {IH: {"name": "MobLand S01", "files": [{"name": "MobLand.S01E03.mkv", "length": 3 * GB}]}}
META = {
    "meta": {
        "name": "MobLand",
        "poster": "p.jpg",
        "videos": [{"season": 1, "episode": 3, "name": "Plan B", "thumbnail": "s.jpg"}],
    }
}


def _handler(request: httpx.Request) -> httpx.Response:
    if "cinemeta" in str(request.url):
        return httpx.Response(200, json=META)
    return httpx.Response(200, json=STATS)


async def _feed(tmp_path: Path, now: list[float]) -> tuple[ActivityFeed, ActivityStore, LogHub]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    db = open_db(tmp_path / "s.db")
    store = ActivityStore(db, clock=lambda: now[0])
    subs = SubtitleStore(db)
    subs.save_file(SubtitleFile(IH, 0, "MobLand.S01E03.mkv", 3 * GB, None, 3270.0, 0, True))
    feed = ActivityFeed(
        store, StremioServer("http://srv", http), subs, Cinemeta(http), lambda: now[0]
    )
    hub = LogHub()
    feed.attach(hub)
    return feed, store, hub


async def _drain(feed: ActivityFeed) -> None:
    runner = asyncio.create_task(feed.run())
    await asyncio.sleep(0.05)
    runner.cancel()


@pytest.mark.asyncio
async def test_a_viewing_session_reads_like_a_story(tmp_path: Path) -> None:
    now = [1000.0]
    feed, store, hub = await _feed(tmp_path, now)
    await feed(ClientSeen("/settings"))
    await feed(ClientSeen("/stats.json"))  # same session: not a second "connected"
    hub.companion_event(
        {
            "event": "addon_subtitles_request",
            "kind": "series",
            "item": "tt31510819:1:3",
            "file": "MobLand.S01E03.mkv",
            "client": "192.168.1.134",
            "info_hash": IH,
            "file_index": 0,
        }
    )
    await _drain(feed)
    await feed(FileRequested(IH, 0, 0))
    now[0] += 30
    await feed(FileRequested(IH, 0, GB))  # a third of the way in: a seek
    await _drain(feed)
    titles = [a.title for a in reversed(store.changed_since(0, 20))]
    assert titles == [
        "The TV connected to this Mac",
        "Opened MobLand · S01E03 · Plan B",
        "Playing MobLand · S01E03 · Plan B",
        "Jumped to 18:10 of 54:30",
    ]
    assert store.changed_since(0, 20)[0].image == "s.jpg"


@pytest.mark.asyncio
async def test_subtitle_windows_coalesce_and_problems_show(tmp_path: Path) -> None:
    now = [1000.0]
    feed, store, hub = await _feed(tmp_path, now)
    for start in (0, 15, 38):
        hub.companion_event(
            {
                "event": "subtitle_window",
                "file": "a/MobLand.S01E03.mkv",
                "start": start,
                "end": start + 15,
                "seconds": 9.1,
            }
        )
    hub.companion_event({"event": "translator_hourly_cap_reached", "calls": 120})
    hub.companion_event({"event": "something_broke", "level": "error", "error": "boom"})
    await _drain(feed)
    by_title = {a.title: a for a in store.changed_since(0, 20)}
    assert "First Romanian subtitles ready" in by_title
    assert by_title["Romanian subtitles: 3 parts"].count == 3
    assert by_title["Hourly translator cap reached"].category == "problem"
    assert by_title["Something broke"].detail == "boom"


@pytest.mark.asyncio
async def test_backfill_rebuilds_history_once_with_its_own_times(tmp_path: Path) -> None:
    now = [5000.0]
    feed, store, hub = await _feed(tmp_path, now)
    hub.companion_event(
        {
            "event": "tv_read",
            "file": "MobLand.S01E03.mkv",
            "progress": 0.35,
            "timestamp": "2026-10-21T10:00:00Z",
        },
        notify=False,
    )
    hub.companion_event(
        {"event": "pinned", "info_hash": IH, "file_index": 0, "timestamp": "2026-10-21T10:00:05Z"},
        notify=False,
    )
    await feed.backfill(hub)
    rows = store.changed_since(0, 10)
    assert [r.title for r in rows] == [
        "Keeping the file downloading, even while paused",
        "Playing MobLand · S01E03",
    ]
    assert rows[1].ts == 1792576800.0
    await feed.backfill(hub)  # not again
    assert len(store.changed_since(0, 10)) == 2


@pytest.mark.parametrize(
    ("raw", "nice"),
    [
        (
            "East.of.Eden.2026.S01E04.Kate.1080p.NF.WEB-DL.DDP5.1.Atmos.H.264.mkv",
            "East of Eden · S01E04 · Kate",
        ),
        ("Pack/MobLand.S01E03.1080p.WEB.H264-SuccessfulCrab.mkv", "MobLand · S01E03"),
        ("Dune.Part.Two.2024.2160p.WEB-DL.mkv", "Dune Part Two"),
    ],
)
def test_release_names_read_like_titles(raw: str, nice: str) -> None:
    assert pretty_name(raw) == nice
