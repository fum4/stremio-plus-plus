from pathlib import Path

import httpx
import pytest

from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.state.plays import Plays
from stremio_plus_plus.watch.events import EngineCreated, FileRequested
from stremio_plus_plus.watch.play_recorder import PlayRecorder

IH = "aa" * 20
STATS = {IH: {"name": "Show", "files": [{"name": "Show.S01E01.mkv", "length": 1000}]}}


@pytest.mark.asyncio
async def test_records_tv_reads_with_file_metadata(tmp_path: Path) -> None:
    server = StremioServer(
        "http://srv",
        httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=STATS))),
    )
    plays = Plays(open_db(tmp_path / "s.db"))
    recorder = PlayRecorder(server, plays, clock=lambda: 42.0)
    await recorder(EngineCreated(IH))
    await recorder(FileRequested(IH, 0, 250))
    await recorder(FileRequested(IH, 9, 0))  # unknown file index: ignored
    play = plays.get(IH, 0)
    assert play is not None
    assert (play.file_name, play.last_offset, play.last_played_at) == ("Show.S01E01.mkv", 250, 42.0)
    assert plays.get(IH, 9) is None
