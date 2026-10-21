"""Engine pins: one idle open-ended read per file.

An open `Range: bytes=0-` stream makes server.js select the whole file (prewarmStream) and keeps
the engine alive (ENGINE_TIMEOUT only starts after the last stream closes) — so a file keeps
downloading after the TV pauses or stops. See docs/research/stremio-internals.md.
"""

import asyncio
import contextlib

import httpx
import structlog

from stremio_plus_plus.server.client import StremioServer

log = structlog.get_logger()
FileKey = tuple[str, int]


class Pinner:
    def __init__(self, http: httpx.AsyncClient, server: StremioServer) -> None:
        self._http = http
        self._server = server
        self._tasks: dict[FileKey, asyncio.Task[None]] = {}

    def pinned(self) -> set[FileKey]:
        return {key for key, task in self._tasks.items() if not task.done()}

    def pin(self, info_hash: str, file_index: int) -> bool:
        key = (info_hash, file_index)
        if key in self.pinned():
            return False
        self._tasks[key] = asyncio.create_task(
            self._hold(key), name=f"pin:{info_hash[:8]}:{file_index}"
        )
        log.info("pinned", info_hash=info_hash, file_index=file_index)
        return True

    async def release(self, info_hash: str, file_index: int) -> None:
        task = self._tasks.pop((info_hash, file_index), None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            log.info("released", info_hash=info_hash, file_index=file_index)

    async def release_engine(self, info_hash: str) -> None:
        for ih, idx in [k for k in self._tasks if k[0] == info_hash]:
            await self.release(ih, idx)

    async def close(self) -> None:
        for ih, idx in list(self._tasks):
            await self.release(ih, idx)

    async def _hold(self, key: FileKey) -> None:
        url = self._server.file_url(*key)
        try:
            async with self._http.stream(
                "GET", url, headers={"Range": "bytes=0-"}, timeout=None
            ) as resp:
                async for _ in resp.aiter_raw(1):
                    break  # one byte proves the stream is open; then sit idle
                await asyncio.Event().wait()
        except httpx.HTTPError as exc:  # engine destroyed or server restarted: the pin just ends
            log.warning("pin_lost", info_hash=key[0], file_index=key[1], error=repr(exc))
