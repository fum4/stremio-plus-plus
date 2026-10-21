"""FastAPI app: routes + the background workers that react to playback, and the admin UI."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from stremio_plus_plus.app import admin, setup, tv_api
from stremio_plus_plus.app.addon import addon_router, lan_router
from stremio_plus_plus.app.https_guard import HttpsGuard
from stremio_plus_plus.app.picker import Picker
from stremio_plus_plus.app.services import HostInfo, Services
from stremio_plus_plus.app.stream_routes import router as stream_router
from stremio_plus_plus.app.subtitle_switch import SubtitleSwitch
from stremio_plus_plus.app.tv_service import TvService
from stremio_plus_plus.config.env import Env
from stremio_plus_plus.config.settings_file import SettingsFile
from stremio_plus_plus.downloads.disk import free_bytes
from stremio_plus_plus.downloads.manager import DownloadManager
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.state.plays import Plays
from stremio_plus_plus.stream.sessions import Sessions
from stremio_plus_plus.subtitles.jobs import SubtitleJobs
from stremio_plus_plus.subtitles.model_cache import ModelDownload
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.subtitles.stt import WhisperMlx
from stremio_plus_plus.subtitles.translators.registry import ConfiguredTranslator
from stremio_plus_plus.watch.clients import ClientMonitor
from stremio_plus_plus.watch.log_tail import follow
from stremio_plus_plus.watch.play_recorder import PlayRecorder
from stremio_plus_plus.watch.tracker import run_tracker

log = structlog.get_logger()
SETTINGS_POLL_S = 2.0


async def _watch_settings(settings_file: SettingsFile) -> None:
    """Pick up edits to config.toml / secrets.toml made outside the UI (by hand, by an agent)."""
    reported: str | None = None
    while True:
        await asyncio.sleep(SETTINGS_POLL_S)
        changed = settings_file.refresh()
        if settings_file.error and settings_file.error != reported:
            log.warning("settings_invalid_keeping_last_good", error=settings_file.error)
        elif changed:
            log.info("settings_reloaded", path=str(settings_file.path))
        reported = settings_file.error


def create_app(env: Env, settings_file: SettingsFile, host: HostInfo) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        db = open_db(env.companion_data_dir / "state.db")
        async with httpx.AsyncClient() as http:
            server = StremioServer(env.server_base, http)
            cache_dir = await server.cache_dir()
            pinner = Pinner(http, server)
            plays = Plays(db)
            subtitle_store = SubtitleStore(db)
            translator = ConfiguredTranslator(settings_file, env.claude_cli)
            clients = ClientMonitor(env.companion_data_dir)
            whisper = WhisperMlx(lambda: settings_file.settings.subtitles.speech)
            subtitles = SubtitleJobs(server, subtitle_store, whisper, translator)
            downloads = DownloadManager(
                server,
                pinner,
                lambda: free_bytes(cache_dir),
                lambda: settings_file.settings.downloads.min_free_bytes,
                subtitles.prepare_next,
            )
            sessions = Sessions(env.companion_data_dir / "hls")
            handlers = [PlayRecorder(server, plays), downloads, subtitles]
            services = Services(
                env=env,
                host=host,
                settings_file=settings_file,
                http=http,
                db=db,
                server=server,
                cache_dir=cache_dir,
                plays=plays,
                pinner=pinner,
                downloads=downloads,
                subtitle_store=subtitle_store,
                subtitles=subtitles,
                picker=Picker(http, server, env.companion_data_dir),
                sessions=sessions,
                playback_handlers=handlers,
                translator=translator,
                model_download=ModelDownload(),
                clients=clients,
                tv=TvService(env, settings_file),
            )
            app.state.services = services
            workers = [
                asyncio.create_task(
                    run_tracker(
                        follow(env.stremio_server_log),
                        [*handlers, SubtitleSwitch(services), clients],
                    ),
                    name="tracker",
                ),
                asyncio.create_task(downloads.run_sweeper(), name="pin-sweeper"),
                asyncio.create_task(subtitles.run(), name="subtitles"),
                asyncio.create_task(whisper.warm(), name="whisper-warm"),
                asyncio.create_task(sessions.run_reaper(), name="hls-reaper"),
                asyncio.create_task(_watch_settings(settings_file), name="settings-watch"),
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
    app.include_router(admin.router)
    app.include_router(setup.router)
    app.include_router(tv_api.router)
    app.add_middleware(HttpsGuard, https_port=env.addon_https_port, token=host.addon_token)

    @app.get("/health")
    async def health() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"status": "ok"}

    # Last: the UI's catch-all must not shadow the routes above. LAN-only like /api (https_guard).
    if (env.ui_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=env.ui_dir, html=True), name="ui")
    else:
        log.warning("admin_ui_not_built", run="mise run ui:build", ui_dir=str(env.ui_dir))

    return app
