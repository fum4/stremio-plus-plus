"""Process entrypoint: load config, resolve this host, serve the app.

Two listeners on one app: plain http on COMPANION_PORT (LAN: UI, health, SRT for the streaming
server) and HTTPS on ADDON_HTTPS_PORT for the TV's addon requests. The HTTPS one starts as soon
as a certificate exists (tls/addon.py) and picks up renewals without a restart.
"""

import asyncio

import httpx
import structlog
import uvicorn

from stremio_plus_plus.app.factory import create_app
from stremio_plus_plus.app.services import HostInfo
from stremio_plus_plus.config import host
from stremio_plus_plus.config.env import Env, load_env
from stremio_plus_plus.config.settings_file import SettingsFile
from stremio_plus_plus.log.setup import configure_logging
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.tls import addon

log = structlog.get_logger()
RETRY_S = 60.0  # no certificate yet (server still starting, no network): try again soon
RECHECK_S = 12 * 3600.0


def _config(app: object, env: Env, port: int, **ssl: object) -> uvicorn.Config:
    return uvicorn.Config(
        app,  # pyright: ignore[reportArgumentType]
        host=env.companion_host,
        port=port,
        log_config=None,
        access_log=False,
        **ssl,  # pyright: ignore[reportArgumentType]
    )


async def _https_supervisor(app: object, env: Env, info: HostInfo) -> None:
    async with httpx.AsyncClient() as http:
        server = StremioServer(env.server_base, http)
        listener: uvicorn.Server | None = None
        task: asyncio.Task[None] | None = None
        while True:
            tls = await addon.resolve(
                env.addon_domain,
                env.tls_dir,
                env.stremio_server_data_dir,
                env.tls_dir / "stremio",
                lambda: server.request_https(str(info.lan_ip)),
            )
            if tls is None:
                hint = "mise run tls:renew" if env.addon_domain else "is the streaming server up?"
                log.warning("https_addon_waiting_for_certificate", hint=hint)
            elif listener is None:
                config = _config(
                    app,
                    env,
                    env.addon_https_port,
                    ssl_certfile=tls.cert_path,
                    ssl_keyfile=tls.key_path,
                    lifespan="off",  # one lifespan (workers, db), run by the http server
                )
                listener = uvicorn.Server(config)
                task = asyncio.create_task(listener.serve(), name="https")
                while not listener.started and not task.done():  # a bad cert fails right here
                    await asyncio.sleep(0.1)
                if task.done():
                    task.result()  # raise the listener's startup error
                log.info("https_addon_serving", mode=tls.mode, domain=tls.domain)
            elif listener.config.ssl is not None and tls != info.tls:
                listener.config.ssl.load_cert_chain(tls.cert_path, tls.key_path)  # new handshakes
                log.info("https_addon_certificate_reloaded", domain=tls.domain)
            info.tls = tls or info.tls
            if task is not None and task.done():
                task.result()  # surface a crashed listener
            await asyncio.sleep(RECHECK_S if tls else RETRY_S)


async def _serve(env: Env) -> None:
    settings_file = SettingsFile(env.config_dir)
    info = HostInfo(
        lan_ip=host.lan_ip(env),
        addon_token=host.addon_token(env, settings_file),
        https_port=env.addon_https_port,
    )
    app = create_app(env, settings_file, info)
    http = uvicorn.Server(_config(app, env, env.companion_port))
    log.info("host", lan_ip=str(info.lan_ip), ui=f"http://{info.lan_ip}:{env.companion_port}/")
    await asyncio.gather(http.serve(), _https_supervisor(app, env, info))


def main() -> None:
    env = load_env()
    configure_logging(level=env.log_level, fmt=env.log_format)
    asyncio.run(_serve(env))
