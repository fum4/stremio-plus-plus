"""In-memory stand-in for the Stremio server, for download tests (not collected by pytest)."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx

from stremio_companion.server.client import StremioServer


class _Idle(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"x"
        await asyncio.Event().wait()


class FakeServer:
    def __init__(self, stats: dict[str, Any], progress: dict[tuple[str, int], float]) -> None:
        self.stats = stats
        self.progress = progress
        self.streams: list[str] = []
        self.http = httpx.AsyncClient(transport=httpx.MockTransport(self._handle))
        self.client = StremioServer("http://srv", self.http)

    def _handle(self, req: httpx.Request) -> httpx.Response:
        parts = req.url.path.strip("/").split("/")
        if parts == ["stats.json"]:
            return httpx.Response(200, json=self.stats)
        if len(parts) == 3 and parts[2] == "stats.json":
            key = (parts[0], int(parts[1]))
            return httpx.Response(200, json={"streamProgress": self.progress.get(key, 0.0)})
        self.streams.append(req.url.path)
        return httpx.Response(206, stream=_Idle())
