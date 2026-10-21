import asyncio
from pathlib import Path

import pytest

from stremio_plus_plus.watch.log_tail import follow


async def _take(path: Path, n: int, **kw: bool) -> list[str]:
    out: list[str] = []
    async for line in follow(path, poll_s=0.01, **kw):
        out.append(line)
        if len(out) == n:
            break
    return out


@pytest.mark.asyncio
async def test_yields_only_new_lines_by_default(tmp_path: Path) -> None:
    log = tmp_path / "server.log"
    log.write_text("old\n")
    task = asyncio.create_task(_take(log, 2))
    await asyncio.sleep(0.05)
    with log.open("a") as f:
        f.write("new 1\nnew ")
        f.flush()
        await asyncio.sleep(0.05)
        f.write("2\n")
    assert await asyncio.wait_for(task, 2) == ["new 1", "new 2"]


@pytest.mark.asyncio
async def test_reopens_after_truncation(tmp_path: Path) -> None:
    log = tmp_path / "server.log"
    log.write_text("a long first line that will be truncated away\n")
    task = asyncio.create_task(_take(log, 1))
    await asyncio.sleep(0.05)
    log.write_text("")
    await asyncio.sleep(0.05)
    log.write_text("fresh\n")
    assert await asyncio.wait_for(task, 2) == ["fresh"]


@pytest.mark.asyncio
async def test_waits_for_the_file_to_appear(tmp_path: Path) -> None:
    log = tmp_path / "late.log"
    task = asyncio.create_task(_take(log, 1, from_start=True))
    await asyncio.sleep(0.05)
    log.write_text("hello\n")
    assert await asyncio.wait_for(task, 2) == ["hello"]
