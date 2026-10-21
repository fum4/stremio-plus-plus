"""Thin async client for the Stremio streaming server's HTTP API (server.js, closed bundle)."""

from typing import Any, cast

import httpx

from stremio_companion.server.constants import COMPANION_TAG, REQUEST_TIMEOUT_S
from stremio_companion.server.models import Engine, TorrentFile


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

    async def remove(self, info_hash: str) -> None:
        resp = await self._http.get(f"{self._base}/{info_hash}/remove", timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
