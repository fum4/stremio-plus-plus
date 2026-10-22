"""Names and posters for what the TV opens, from Cinemeta (Stremio's public metadata addon).

The TV's addon requests carry the catalog id (`tt31510819:1:3`); this turns it into
"MobLand · S01E03 Plan B" with a poster for the activity feed. Looked up once per id, cached.
"""

from dataclasses import dataclass
from typing import Any, cast

import httpx
import structlog

log = structlog.get_logger()
BASE = "https://v3-cinemeta.strem.io/meta"
TIMEOUT_S = 6.0


@dataclass(frozen=True)
class Title:
    name: str
    subtitle: str | None  # "S01E03 · Plan B" for an episode
    poster: str | None
    still: str | None  # the episode's thumbnail, when there is one
    year: str | None


def _parse_id(item_id: str) -> tuple[str, int | None, int | None] | None:
    parts = item_id.split(":")
    if not parts[0].startswith("tt"):
        return None  # kitsu and friends: Cinemeta doesn't know them
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        return parts[0], int(parts[1]), int(parts[2])
    return parts[0], None, None


def parse_meta(meta: dict[str, Any], season: int | None, episode: int | None) -> Title:
    subtitle = still = None
    if season is not None and episode is not None:
        subtitle = f"S{season:02d}E{episode:02d}"
        for video in cast(list[dict[str, Any]], meta.get("videos") or []):
            number = video.get("episode", video.get("number"))
            if video.get("season") == season and number == episode:
                if name := video.get("name") or video.get("title"):
                    subtitle += f" · {name}"
                still = video.get("thumbnail")
                break
    return Title(
        name=str(meta.get("name") or "Unknown"),
        subtitle=subtitle,
        poster=meta.get("poster"),
        still=still,
        year=meta.get("year") or meta.get("releaseInfo"),
    )


class Cinemeta:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http
        self._cache: dict[str, Title | None] = {}

    async def title(self, kind: str, item_id: str) -> Title | None:
        if item_id in self._cache:
            return self._cache[item_id]
        parsed = _parse_id(item_id)
        result: Title | None = None
        if parsed is not None:
            imdb, season, episode = parsed
            try:
                resp = await self._http.get(f"{BASE}/{kind}/{imdb}.json", timeout=TIMEOUT_S)
                resp.raise_for_status()
                meta = cast(dict[str, Any], resp.json().get("meta") or {})
                result = parse_meta(meta, season, episode) if meta else None
            except (httpx.HTTPError, ValueError) as exc:
                log.debug("cinemeta_lookup_failed", item=item_id, error=str(exc))
                return None  # not cached: try again next time
        self._cache[item_id] = result
        return result
