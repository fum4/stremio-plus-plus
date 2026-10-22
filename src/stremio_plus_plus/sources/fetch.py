"""Ask every stream addon the viewer has installed for an item's streams, all at once."""

import asyncio
from typing import Any, cast
from urllib.parse import quote

import httpx
import structlog

from stremio_plus_plus.sources.candidates import Candidate, parse
from stremio_plus_plus.sources.constants import (
    DEFAULT_ADDONS,
    FETCH_TIMEOUT_S,
    OWN_ADDON_ID,
    SKIP_ADDON_IDS,
    USER_AGENT,
)

log = structlog.get_logger()
HEADERS = {"User-Agent": USER_AGENT}


def _serves(manifest: dict[str, Any], kind: str, item_id: str) -> bool:
    if manifest.get("id") in SKIP_ADDON_IDS or str(manifest.get("id", "")).startswith(OWN_ADDON_ID):
        return False
    prefixes = cast(list[str] | None, manifest.get("idPrefixes"))
    types = cast(list[str], manifest.get("types") or [])
    for resource in cast(list[Any], manifest.get("resources") or []):
        if isinstance(resource, str):
            if resource == "stream":
                break
        elif isinstance(resource, dict) and cast(dict[str, Any], resource).get("name") == "stream":
            res = cast(dict[str, Any], resource)
            types = cast(list[str], res.get("types") or types)
            prefixes = cast(list[str] | None, res.get("idPrefixes") or prefixes)
            break
    else:
        return False
    return kind in types and (not prefixes or any(item_id.startswith(p) for p in prefixes))


def stream_addons(addons: list[dict[str, Any]] | None, kind: str, item_id: str) -> list[str]:
    """Base URLs of the account's addons that serve streams for this item, in their order;
    Stremio's defaults without an account (or when its collection couldn't be read).
    The URLs can embed debrid keys: never log them."""
    bases = [
        str(a["transportUrl"]).removesuffix("/manifest.json")
        for a in addons or []
        if _serves(cast(dict[str, Any], a.get("manifest") or {}), kind, item_id)
        and str(a.get("transportUrl", "")).startswith("https://")
    ]
    return bases or list(DEFAULT_ADDONS)


async def _one(http: httpx.AsyncClient, base: str, kind: str, item_id: str) -> list[Candidate]:
    url = f"{base}/stream/{kind}/{quote(item_id, safe=':')}.json"
    try:
        resp = await http.get(url, timeout=FETCH_TIMEOUT_S, follow_redirects=True, headers=HEADERS)
        resp.raise_for_status()
        streams = cast(list[dict[str, Any]], resp.json().get("streams") or [])
    except httpx.HTTPError, ValueError, AttributeError:
        log.warning("addon_streams_failed", addon=base.split("/")[2])
        return []
    host = base.split("/")[2]
    return [c for s in streams if (c := parse(host, s)) is not None]


async def candidates(
    http: httpx.AsyncClient, addons: list[str], kind: str, item_id: str
) -> list[Candidate]:
    results = await asyncio.gather(*(_one(http, base, kind, item_id) for base in addons))
    return [c for batch in results for c in batch]
