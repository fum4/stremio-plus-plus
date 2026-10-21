"""FastAPI app: routes + the background workers that react to playback."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stremio_companion.app.addon import router as addon_router
from stremio_companion.app.services import Services
from stremio_companion.config.env import Env
from stremio_companion.downloads.disk import free_bytes
from stremio_companion.downloads.manager import DownloadManager
from stremio_companion.downloads.pins import Pinner
from stremio_companion.server.client import StremioServer
from stremio_companion.state.db import open_db
from stremio_companion.state.plays import Plays
from stremio_companion.subtitles.jobs import SubtitleJobs
from stremio_companion.subtitles.store import SubtitleStore
from stremio_companion.subtitles.stt import WhisperMlx
from stremio_companion.subtitles.translate import ClaudeCliTranslator
from stremio_companion.watch.log_tail import follow
from stremio_companion.watch.play_recorder import PlayRecorder
from stremio_companion.watch.tracker import run_tracker

log = structlog.get_logger()


def create_app(env: Env) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        db = open_db(env.companion_data_dir / "state.db")
        async with httpx.AsyncClient() as http:
            server = StremioServer(env.server_base, http)
            cache_dir = await server.cache_dir()
            pinner = Pinner(http, server)
            plays = Plays(db)
            downloads = DownloadManager(server, pinner, lambda: free_bytes(cache_dir))
            subtitle_store = SubtitleStore(db)
            subtitles = SubtitleJobs(
                server, subtitle_store, WhisperMlx(), ClaudeCliTranslator(env.claude_cli)
            )
            services = Services(
                env=env,
                http=http,
                db=db,
                server=server,
                plays=plays,
                pinner=pinner,
                downloads=downloads,
                subtitle_store=subtitle_store,
                subtitles=subtitles,
            )
            app.state.services = services
            workers = [
                asyncio.create_task(
                    run_tracker(
                        follow(env.stremio_server_log),
                        [PlayRecorder(server, plays), downloads, subtitles],
                    ),
                    name="tracker",
                ),
                asyncio.create_task(downloads.run_sweeper(), name="pin-sweeper"),
                asyncio.create_task(subtitles.run(), name="subtitles"),
            ]
            log.info(
                "companion_started", data_dir=str(env.companion_data_dir), cache_dir=str(cache_dir)
            )
            try:
                yield
            finally:
                for worker in workers:
                    worker.cancel()
                await pinner.close()
                db.close()

    app = FastAPI(title="stremio-companion", lifespan=lifespan)
    # Stremio clients fetch addon resources cross-origin.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
    app.include_router(addon_router)

    @app.get("/health")
    async def health() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"status": "ok"}

    return app
