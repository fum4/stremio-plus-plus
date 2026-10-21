"""Process entrypoint: load config, configure logging, serve the app.

Two listeners on one app: plain http on COMPANION_PORT (LAN: health, SRT for the streaming server)
and, once a certificate exists, HTTPS on ADDON_HTTPS_PORT for the TV's addon requests.
"""

import asyncio

import structlog
import uvicorn

from stremio_companion.app.factory import create_app
from stremio_companion.config.env import Env, load_env
from stremio_companion.log.setup import configure_logging
from stremio_companion.tls.paths import cert_paths


async def _serve(env: Env) -> None:
    app = create_app(env)
    servers = [
        uvicorn.Server(
            uvicorn.Config(
                app,
                host=env.companion_host,
                port=env.companion_port,
                log_config=None,
                access_log=False,
            )
        )
    ]
    cert, key = cert_paths(env.tls_dir, env.addon_domain)
    if cert.is_file() and key.is_file():
        https = uvicorn.Config(
            app,
            port=env.addon_https_port,
            ssl_certfile=cert,
            ssl_keyfile=key,
            lifespan="off",  # one lifespan (workers, db) for the app, run by the http server
            host=env.companion_host,
            log_config=None,
            access_log=False,
        )
        servers.append(uvicorn.Server(https))
    else:
        structlog.get_logger().warning(
            "https_addon_disabled_no_certificate", run="mise run tls:renew"
        )
    await asyncio.gather(*(server.serve() for server in servers))


def main() -> None:
    env = load_env()
    configure_logging(level=env.log_level, fmt=env.log_format)
    asyncio.run(_serve(env))
