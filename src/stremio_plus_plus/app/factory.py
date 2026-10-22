"""FastAPI app: routes + the background workers that react to playback."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stremio_plus_plus.app.addon import addon_router, lan_router
from stremio_plus_plus.app.https_guard import HttpsGuard
from stremio_plus_plus.app.picker import Picker
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.app.stream_routes import router as stream_router
from stremio_plus_plus.app.subtitle_switch import SubtitleSwitch
from stremio_plus_plus.config.env import Env
from stremio_plus_plus.downloads.disk import free_bytes
from stremio_plus_plus.downloads.manager import DownloadManager
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.state.plays import Plays
from stremio_plus_plus.stream.sessions import Sessions
from stremio_plus_plus.subtitles.jobs import SubtitleJobs
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.subtitles.stt import WhisperMlx
from stremio_plus_plus.subtitles.translate import ClaudeCliTranslator
from stremio_plus_plus.watch.log_tail import follow
from stremio_plus_plus.watch.play_recorder import PlayRecorder
from stremio_plus_plus.watch.tracker import run_tracker

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
            subtitle_store = SubtitleStore(db)
            whisper = WhisperMlx()
            subtitles = SubtitleJobs(
                server, subtitle_store, whisper, ClaudeCliTranslator(env.claude_cli)
            )
            downloads = DownloadManager(
                server, pinner, lambda: free_bytes(cache_dir), subtitles.prepare_next
            )
            sessions = Sessions(env.companion_data_dir / "hls")
            handlers = [PlayRecorder(server, plays), downloads, subtitles]
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
                picker=Picker(http, server, env.companion_data_dir),
                sessions=sessions,
                playback_handlers=handlers,
            )
            app.state.services = services
            workers = [
                asyncio.create_task(
                    run_tracker(
                        follow(env.stremio_server_log), [*handlers, SubtitleSwitch(services)]
                    ),
                    name="tracker",
                ),
                asyncio.create_task(downloads.run_sweeper(), name="pin-sweeper"),
                asyncio.create_task(subtitles.run(), name="subtitles"),
                asyncio.create_task(whisper.warm(), name="whisper-warm"),
                asyncio.create_task(sessions.run_reaper(), name="hls-reaper"),
            ]
            log.info(
                "companion_started", data_dir=str(env.companion_data_dir), cache_dir=str(cache_dir)
            )
            try:
                yield
            finally:
                for worker in workers:
                    worker.cancel()
                await sessions.close()
                await pinner.close()
                db.close()

    # No /docs or /openapi.json: the addon is reachable from outside the LAN (HTTPS front).
    app = FastAPI(
        title="stremio++",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # Stremio clients fetch addon resources cross-origin.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
    app.include_router(addon_router)
    app.include_router(stream_router)
    app.include_router(lan_router)
    app.add_middleware(HttpsGuard, https_port=env.addon_https_port, token=env.addon_token)

    @app.get("/health")
    async def health() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"status": "ok"}

    return app
