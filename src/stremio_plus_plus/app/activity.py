"""The activity feed: what the TV and this host did, as a readable timeline (state/activity.py).

Fed by the server-log tracker (TV connected, reads → playing / seeks, torrents) and by the log
hub (companion events: subtitles, downloads, setup; activity_rules.py). Titles and posters come
from the TV's own addon requests, looked up on Cinemeta.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog

from stremio_plus_plus.app.activity_rules import clock, companion_line, pretty_name
from stremio_plus_plus.log.hub import Entry, LogHub
from stremio_plus_plus.meta.cinemeta import Cinemeta, Title
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.activity import ActivityStore
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.watch.events import (
    ClientSeen,
    EngineCreated,
    EngineDestroyed,
    Event,
    FileRequested,
)

log = structlog.get_logger()
TV_GAP_S = 15 * 60  # a client request after this long reads as "the TV connected" again
PLAY_GAP_S = 10 * 60  # reads of a file after this long are a new "playing", not a seek
SEEK_MIN_BYTES = 64 * 1024**2
TAIL_FRACTION = 0.98  # MKV index reads at the end of the file aren't the playhead


@dataclass
class _File:
    name: str = ""
    length: int = 0
    offset: int = 0
    last_read: float = 0.0
    title: Title | None = None


class ActivityFeed:
    def __init__(
        self,
        store: ActivityStore,
        server: StremioServer,
        subtitles: SubtitleStore,
        cinemeta: Cinemeta,
        clock_: Callable[[], float] = time.time,
    ) -> None:
        self._store = store
        self._server = server
        self._subtitles = subtitles
        self._cinemeta = cinemeta
        self._clock = clock_
        self._queue: asyncio.Queue[Event | Entry] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._files: dict[tuple[str, int], _File] = {}
        self._client_seen = 0.0
        self._windows: dict[str, int] = {}  # file → parts generated this session
        self._at: float | None = None  # set while backfilling: the history entry's time

    def _add(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self._store.add(*args, **kwargs, at=self._at)

    async def backfill(self, hub: LogHub) -> None:
        """First start: rebuild the timeline from the companion's timestamped log history.
        Server lines carry no time, so TV reads come from the companion's `tv_read` events."""
        if not self._store.empty():
            return
        for entry in hub.since(0, 100_000):
            if entry.source != "companion" or entry.ts is None:
                continue
            self._at = entry.ts
            try:
                if entry.event == "tv_read":
                    progress = float(str(entry.fields.get("progress") or 0))
                    if progress > TAIL_FRACTION:  # the player reading the MKV index
                        continue
                    name = pretty_name(entry.fields.get("file"))
                    self._add(
                        "playback",
                        "play",
                        f"Playing {name}",
                        f"at {round(progress * 100)}%",
                        key=f"backfill-play:{name}",
                        within_s=PLAY_GAP_S,
                    )
                else:
                    await self._companion(entry)
            except Exception:
                log.debug("activity_backfill_item_failed", exc_info=True)
        self._at = None

    def attach(self, hub: LogHub) -> None:
        self._loop = asyncio.get_running_loop()
        hub.listeners.append(self._from_hub)

    def _from_hub(self, entry: Entry) -> None:  # any thread: logging can happen anywhere
        if entry.source == "companion" and self._loop is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, entry)

    async def __call__(self, event: Event) -> None:  # a tracker handler
        self._queue.put_nowait(event)

    async def run(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                if isinstance(item, Entry):
                    await self._companion(item)
                else:
                    await self._server_event(item)
            except Exception:  # the feed must never take the companion down
                log.debug("activity_item_failed", exc_info=True)

    def _file(self, info_hash: str, index: int) -> _File:
        return self._files.setdefault((info_hash, index), _File())

    def _label(self, f: _File) -> tuple[str, str | None]:
        if f.title:
            name = f.title.name + (f" · {f.title.subtitle}" if f.title.subtitle else "")
            return name, f.title.still or f.title.poster
        return (pretty_name(f.name) or "a video"), None

    async def _server_event(self, event: Event) -> None:
        now = self._clock()
        if isinstance(event, ClientSeen):
            if now - self._client_seen > TV_GAP_S:
                self._add("playback", "tv", "The TV connected to this Mac", event.path)
            self._client_seen = now
        elif isinstance(event, EngineCreated | EngineDestroyed):
            engine = (await self._server.engines()).get(event.info_hash)
            name = engine.name if engine else event.info_hash[:12]
            created = isinstance(event, EngineCreated)
            self._add(
                "downloads",
                "torrent",
                "Torrent started" if created else "Torrent closed",
                name,
                key=f"engine:{event.info_hash}:{created}",
                within_s=600,
            )
        elif isinstance(event, FileRequested):
            await self._read(event, now)
        # SubtitleFetched: the player loading a track; ours shows up as srt_served instead.

    async def _read(self, event: FileRequested, now: float) -> None:
        f = self._file(event.info_hash, event.file_index)
        if not f.length:
            engine = (await self._server.engines()).get(event.info_hash)
            file = engine.file(event.file_index) if engine else None
            if file:
                f.name, f.length = file.name, file.length
        if f.length and event.offset > f.length * TAIL_FRACTION:
            return
        label, image = self._label(f)
        where = self._position(event.info_hash, event.file_index, event.offset, f.length)
        key = f"{event.info_hash}:{event.file_index}"
        if now - f.last_read > PLAY_GAP_S:
            self._add(
                "playback", "play", f"Playing {label}", where, image, key=f"play:{key}", within_s=60
            )
        elif abs(event.offset - f.offset) > max(SEEK_MIN_BYTES, f.length * 0.03):
            self._add(
                "playback",
                "seek",
                f"Jumped to {where}",
                label,
                image,
                key=f"seek:{key}",
                within_s=20,
            )
        f.offset, f.last_read = event.offset, now

    def _position(self, info_hash: str, index: int, offset: int, length: int) -> str:
        meta = self._subtitles.file(info_hash, index)
        if meta and length:
            return f"{clock(offset / length * meta.duration_s)} of {clock(meta.duration_s)}"
        return f"{round(offset / length * 100)}%" if length else "the start"

    async def _companion(self, entry: Entry) -> None:
        fields = entry.fields
        if entry.event == "addon_subtitles_request":
            await self._opened(fields)
        elif entry.event == "subtitle_window":
            self._window(fields)
        elif line := companion_line(entry.event or "", fields, entry.level):
            self._add(
                line.category,
                line.kind,
                line.title,
                line.detail,
                key=line.key,
                within_s=line.within_s,
            )

    async def _opened(self, fields: dict[str, object]) -> None:
        title = await self._cinemeta.title(str(fields.get("kind")), str(fields.get("item")))
        name = (
            (title.name + (f" · {title.subtitle}" if title and title.subtitle else ""))
            if title
            else str(fields.get("file") or fields.get("item"))
        )
        image = (title.still or title.poster) if title else None
        if fields.get("info_hash") is not None:
            f = self._file(str(fields["info_hash"]), int(str(fields["file_index"])))
            f.title = title
            detail = f"from {fields.get('client')}" if fields.get("client") else None
        else:
            detail = "not streaming through this Mac: no AI subtitles for it"
        self._add(
            "playback",
            "open",
            f"Opened {name}",
            detail,
            image,
            key=f"open:{fields.get('item')}",
            within_s=600,
        )

    def _window(self, fields: dict[str, object]) -> None:
        file = str(fields.get("file"))
        count = self._windows.get(file, 0) + 1
        self._windows[file] = count
        start, end = float(str(fields.get("start") or 0)), float(str(fields.get("end") or 0))
        short = pretty_name(file)
        if count == 1:
            self._add(
                "subtitles",
                "first",
                "First Romanian subtitles ready",
                f"{short} · after {fields.get('seconds')} s",
            )
        self._add(
            "subtitles",
            "progress",
            f"Romanian subtitles: {int(count)} parts",
            f"{short} · latest {clock(start)}-{clock(end)} in {fields.get('seconds')} s",
            key=f"subs:{file}",
            within_s=3600,
        )
