"""Process entrypoint: load config, configure logging, start the service."""

import structlog

from stremio_companion.config.env import load_env
from stremio_companion.log.setup import configure_logging


def main() -> None:
    env = load_env()
    configure_logging(level=env.log_level, fmt=env.log_format)
    structlog.get_logger().info(
        "boot",
        stremio_server_url=str(env.stremio_server_url),
        host=env.companion_host,
        port=env.companion_port,
    )
