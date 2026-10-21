"""Process entrypoint: load config, configure logging, serve the app."""

import uvicorn

from stremio_companion.app.factory import create_app
from stremio_companion.config.env import load_env
from stremio_companion.log.setup import configure_logging


def main() -> None:
    env = load_env()
    configure_logging(level=env.log_level, fmt=env.log_format)
    uvicorn.run(
        create_app(env),
        host=env.companion_host,
        port=env.companion_port,
        log_config=None,
        access_log=False,
    )
