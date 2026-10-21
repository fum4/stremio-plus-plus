"""Daily cleanup job (launchd `cleanup` agent; `mise run cleanup [-- --dry-run]`)."""

import argparse
import asyncio
import shutil
import time

import httpx
import structlog

from stremio_plus_plus.config.env import load_env
from stremio_plus_plus.downloads.cleanup import plan_cleanup, scan_cache
from stremio_plus_plus.downloads.constants import MIN_FREE_BYTES, STALE_AFTER_S
from stremio_plus_plus.downloads.disk import free_bytes
from stremio_plus_plus.log.setup import configure_logging
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.state.plays import Plays

log = structlog.get_logger()


async def run_cleanup(*, dry_run: bool) -> None:
    env = load_env()
    async with httpx.AsyncClient() as http:
        server = StremioServer(env.server_base, http)
        # Server down = fail: without the live-engine list nothing is safe to delete.
        active = set(await server.engines())
        cache_dir = await server.cache_dir()
    db = open_db(env.companion_data_dir / "state.db")
    try:
        plays = Plays(db)
        torrents = scan_cache(cache_dir, plays.last_played_per_torrent())
        doomed = plan_cleanup(
            torrents,
            active,
            now=time.time(),
            free_bytes=free_bytes(cache_dir),
            stale_after_s=STALE_AFTER_S,
            min_free_bytes=MIN_FREE_BYTES,
        )
        for torrent in doomed:
            age_days = round((time.time() - torrent.last_used) / 86400, 1)
            log.info(
                "cleanup_delete",
                info_hash=torrent.info_hash,
                gb=round(torrent.size_bytes / 1024**3, 2),
                idle_days=age_days,
                dry_run=dry_run,
            )
            if not dry_run:
                shutil.rmtree(torrent.path)
                plays.forget_torrent(torrent.info_hash)
        log.info(
            "cleanup_done",
            scanned=len(torrents),
            deleted=len(doomed),
            active=len(active),
            dry_run=dry_run,
        )
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="log what would be deleted, delete nothing"
    )
    args = parser.parse_args()
    env = load_env()
    configure_logging(level=env.log_level, fmt=env.log_format)
    asyncio.run(run_cleanup(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
