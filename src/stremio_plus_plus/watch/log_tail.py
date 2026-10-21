"""Follow a growing log file (like `tail -F`): survives truncation, rotation and late creation."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from stremio_plus_plus.watch.constants import POLL_INTERVAL_S


async def follow(
    path: Path, *, from_start: bool = False, poll_s: float = POLL_INTERVAL_S
) -> AsyncIterator[str]:
    while not path.exists():
        await asyncio.sleep(poll_s)
    handle = path.open("r", encoding="utf-8", errors="replace")
    inode = path.stat().st_ino
    if not from_start:
        handle.seek(0, 2)
    pending = ""
    try:
        while True:
            chunk = handle.readline()
            if chunk:
                pending += chunk
                if pending.endswith("\n"):
                    yield pending.rstrip("\n")
                    pending = ""
                continue
            await asyncio.sleep(poll_s)
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            if stat.st_ino != inode or stat.st_size < handle.tell():
                handle.close()
                handle = path.open("r", encoding="utf-8", errors="replace")
                inode, pending = stat.st_ino, ""
    finally:
        handle.close()
