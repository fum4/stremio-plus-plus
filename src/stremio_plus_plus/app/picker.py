"""Choose what the Stremio++ entry plays for an item, and turn that choice into a Source once
the player opens it (starting the torrent only then)."""

import hashlib
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.sources.candidates import Candidate
from stremio_plus_plus.sources.fetch import candidates, stream_addons
from stremio_plus_plus.sources.ranking import rank
from stremio_plus_plus.stream.session import Source

log = structlog.get_logger()
_TORRENT_KEY = re.compile(r"^([0-9a-f]{40})-(\d+)$")


@dataclass(frozen=True)
class Offer:
    key: str
    item_id: str
    candidate: Candidate

    @property
    def file(self) -> tuple[str, int]:
        """The (info hash, file index) subtitle jobs will key this source by."""
        c = self.candidate
        if c.info_hash is None:
            return _pseudo_hash(c.url or ""), 0
        return c.info_hash, c.file_index or 0


def _pseudo_hash(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()  # an id, not security


def _key(c: Candidate) -> str:
    if c.info_hash is not None:
        return f"{c.info_hash}-{c.file_index or 0}"
    return hashlib.sha256((c.url or "").encode()).hexdigest()[:24]


def _show(item_id: str) -> str:
    return item_id.split(":", 1)[0]


class Picker:
    def __init__(
        self,
        http: httpx.AsyncClient,
        server: StremioServer,
        collection: Callable[[], Awaitable[list[dict[str, Any]] | None]],
    ) -> None:
        self._http = http
        self._server = server
        self._collection = collection  # the account's addons (account/service.py), or None
        self._offers: dict[str, Offer] = {}
        self._by_item: dict[str, str] = {}
        self._last_group: dict[str, str] = {}  # show → bingeGroup of the release last played

    async def pick(self, kind: str, item_id: str) -> Offer | None:
        addons = stream_addons(await self._collection(), kind, item_id)
        found = await candidates(self._http, addons, kind, item_id)
        local = dict.fromkeys(await self._server.engines(), 1.0)
        ranked = rank(found, local, self._last_group.get(_show(item_id)))
        best = next((c for c in ranked if c.playable), None)
        log.info(
            "stream_picked",
            item=item_id,
            addons=len(addons),
            candidates=len(found),
            file=best.filename if best else None,
            height=best.height if best else None,
            seeders=best.seeders if best else None,
        )
        if best is None:
            return None
        offer = Offer(_key(best), item_id, best)
        self._offers[offer.key] = offer
        self._by_item[item_id] = offer.key
        return offer

    def offered_for(self, item_id: str) -> Offer | None:
        key = self._by_item.get(item_id)
        return self._offers.get(key) if key else None

    def offered_file(self, info_hash: str, file_index: int) -> bool:
        return any(o.file == (info_hash, file_index) for o in self._offers.values())

    async def resolve(self, key: str) -> Source | None:
        offer = self._offers.get(key)
        if offer is None:  # offered before a restart (a resumed episode): the key says enough
            if not (m := _TORRENT_KEY.match(key)):
                return None
            offer = Offer(key, "", Candidate("", "", "", m[1], int(m[2])))
        c = offer.candidate
        if c.binge_group and offer.item_id:
            self._last_group[_show(offer.item_id)] = c.binge_group
        if c.info_hash is None:  # a direct (debrid) link: subtitles keyed by the link itself
            # Size unknown for most links; any constant works for playhead fractions.
            return Source(key, c.url or "", *offer.file, c.filename, c.size_bytes or 1 << 40)
        engine = await self._server.create(c.info_hash, c.trackers)
        index = c.file_index if c.file_index is not None else _largest(engine.files)
        file = engine.file(index)
        if file is None:
            log.warning("stream_file_missing", file=c.filename, index=index)
            return None
        url = self._server.file_url(c.info_hash, index)
        return Source(key, url, c.info_hash, index, file.name, file.length)


def _largest(files: tuple[object, ...]) -> int:
    lengths = [getattr(f, "length", 0) for f in files]
    return lengths.index(max(lengths)) if lengths else 0
