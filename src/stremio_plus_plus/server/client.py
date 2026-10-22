"""Thin async client for the Stremio streaming server's HTTP API (server.js, closed bundle)."""

from pathlib import Path
from typing import Any, cast

import httpx

from stremio_plus_plus.server.constants import (
    CACHE_SUBDIR,
    COMPANION_TAG,
    CREATE_TIMEOUT_S,
    OPENSUB_HASH_TIMEOUT_S,
    PEERS_MAX,
    PEERS_MIN,
    REQUEST_TIMEOUT_S,
)
from stremio_plus_plus.server.models import Engine, TorrentFile


def _parse_engine(info_hash: str, raw: dict[str, Any]) -> Engine:
    files = tuple(
        TorrentFile(index=i, name=str(f.get("name", "")), length=int(f.get("length", 0)))
        for i, f in enumerate(cast(list[dict[str, Any]], raw.get("files") or []))
    )
    return Engine(
        info_hash=info_hash,
        name=str(raw.get("name", "")),
        files=files,
        downloaded=int(raw.get("downloaded") or 0),
        download_speed=float(raw.get("downloadSpeed") or 0),
        peers=int(raw.get("peers") or 0),
    )


class StremioServer:
    def __init__(self, base_url: str, http: httpx.AsyncClient) -> None:
        self._base = base_url.rstrip("/")
        self._http = http

    def file_url(self, info_hash: str, file_index: int) -> str:
        """URL our own readers use; tagged so the watch tracker ignores it."""
        return f"{self._base}/{info_hash}/{file_index}?{COMPANION_TAG}"

    async def engines(self) -> dict[str, Engine]:
        resp = await self._http.get(f"{self._base}/stats.json", timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        data = cast(dict[str, dict[str, Any]], resp.json())
        return {ih: _parse_engine(ih, raw) for ih, raw in data.items()}

    async def file_progress(self, info_hash: str, file_index: int) -> float | None:
        """Fraction of the file's pieces on disk (`streamProgress`), None if the engine is gone."""
        resp = await self._http.get(
            f"{self._base}/{info_hash}/{file_index}/stats.json", timeout=REQUEST_TIMEOUT_S
        )
        if resp.status_code != 200 or not resp.content.strip():
            return None
        data = cast(dict[str, Any] | None, resp.json())
        return float(data.get("streamProgress") or 0) if data else None

    async def cache_dir(self) -> Path:
        """`<cacheRoot>/stremio-cache`: one sub-directory per info hash (server.js getCachePath)."""
        resp = await self._http.get(f"{self._base}/settings", timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        values = cast(dict[str, Any], resp.json()["values"])
        return Path(str(values["cacheRoot"])) / CACHE_SUBDIR

    async def opensub_hash(self, video_url: str) -> str | None:
        """OpenSubtitles hash computed by the server from the file (never trust a client's)."""
        resp = await self._http.get(
            f"{self._base}/opensubHash",
            params={"videoUrl": video_url},
            timeout=OPENSUB_HASH_TIMEOUT_S,
        )
        resp.raise_for_status()
        result = cast(dict[str, Any] | None, resp.json().get("result"))
        return str(result["hash"]) if result and result.get("hash") else None

    async def create(self, info_hash: str, trackers: tuple[str, ...] = ()) -> Engine:
        """Start (or join) the torrent the way Stremio clients do, with the addon's trackers."""
        body: dict[str, Any] = {"torrent": {"infoHash": info_hash}}
        if trackers:
            sources = [*trackers, f"dht:{info_hash}"]
            body["peerSearch"] = {"sources": sources, "min": PEERS_MIN, "max": PEERS_MAX}
        resp = await self._http.post(
            f"{self._base}/{info_hash}/create", json=body, timeout=CREATE_TIMEOUT_S
        )
        resp.raise_for_status()
        return _parse_engine(info_hash, cast(dict[str, Any], resp.json()))

    async def remove(self, info_hash: str) -> None:
        resp = await self._http.get(f"{self._base}/{info_hash}/remove", timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
