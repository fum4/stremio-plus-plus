from ipaddress import IPv4Address
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl

from stremio_companion.app.addon import router
from stremio_companion.app.services import Services
from stremio_companion.config.env import Env
from stremio_companion.downloads.manager import DownloadManager
from stremio_companion.downloads.pins import Pinner
from stremio_companion.server.client import StremioServer
from stremio_companion.state.db import open_db
from stremio_companion.state.plays import Plays
from stremio_companion.subtitles.cues import Cue
from stremio_companion.subtitles.jobs import SubtitleJobs
from stremio_companion.subtitles.store import SubtitleStore
from stremio_companion.subtitles.translate import ClaudeCliTranslator

IH = "ab" * 20
STATS = {
    IH: {
        "name": "MobLand S01",
        "files": [{"name": "Pack/MobLand.S01E03.mkv", "length": 3560556831}],
    }
}


class _NoStt:
    async def transcribe(self, audio: object, offset_s: float) -> list[Cue]:
        raise AssertionError("not used in route tests")


def _client(tmp_path: Path) -> tuple[TestClient, SubtitleStore]:
    env = Env(
        stremio_server_url=AnyHttpUrl("http://srv:11470"),
        stremio_server_log=tmp_path / "server.log",
        companion_host="0.0.0.0",
        companion_port=11471,
        companion_data_dir=tmp_path,
        host_lan_ip=IPv4Address("192.168.1.132"),
        claude_cli=Path("/bin/false"),
        log_level="INFO",
        log_format="json",
    )
    http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=STATS))
    )
    server = StremioServer("http://srv:11470", http)
    db = open_db(tmp_path / "s.db")
    store = SubtitleStore(db)
    pinner = Pinner(http, server)
    app = FastAPI()
    app.include_router(router)
    app.state.services = Services(
        env=env,
        http=http,
        db=db,
        server=server,
        plays=Plays(db),
        pinner=pinner,
        downloads=DownloadManager(server, pinner, lambda: 0),
        subtitle_store=store,
        subtitles=SubtitleJobs(server, store, _NoStt(), ClaudeCliTranslator(Path("/bin/false"))),
    )
    return TestClient(app), store


def test_manifest_names_the_addon_romanian_ai(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.get("/manifest.json").json()["name"] == "Romanian (AI)"


def test_subtitles_request_matches_the_playing_file_by_name(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    resp = client.get(
        "/subtitles/series/tt31510819:1:3/filename=MobLand.S01E03.mkv&videoSize=3560556831&videoHash=1e89.json"
    )
    [track] = resp.json()["subtitles"]
    assert track["lang"] == "ron" and track["label"] == "Romanian (AI)"
    assert track["url"] == f"http://192.168.1.132:11471/srt/{IH}/0.srt"


def test_unknown_file_gets_no_track(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.get("/subtitles/movie/tt1/filename=Other.mkv.json").json() == {"subtitles": []}


def test_srt_serves_stored_cues_or_a_placeholder(tmp_path: Path) -> None:
    client, store = _client(tmp_path)
    assert "Se generează" in client.get(f"/srt/{IH}/0.srt").text
    store.save_chunk(IH, 0, 0, [Cue(1.0, 2.0, "Unu")])
    assert client.get(f"/srt/{IH}/0.srt").text == "1\n00:00:01,000 --> 00:00:02,000\nUnu\n"
