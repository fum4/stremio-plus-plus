from ipaddress import IPv4Address
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl

from stremio_plus_plus.app.addon import addon_router, lan_router
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.config.env import Env
from stremio_plus_plus.downloads.manager import DownloadManager
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.state.plays import Plays
from stremio_plus_plus.subtitles.cues import Cue
from stremio_plus_plus.subtitles.jobs import SubtitleJobs
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.subtitles.translate import ClaudeCliTranslator

IH = "ab" * 20
TOKEN = "k" * 32
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
        tv_host=IPv4Address("192.168.1.134"),
        addon_domain="stremio.nomadware.io",
        addon_https_port=8443,
        addon_token=TOKEN,
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
    app.include_router(addon_router)
    app.include_router(lan_router)
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


def test_manifest_names_the_addon_stremio_plus_plus(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.get(f"/{TOKEN}/manifest.json").json()["name"] == "Stremio++"


def test_subtitles_request_matches_the_playing_file_by_name(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    resp = client.get(
        f"/{TOKEN}/subtitles/series/tt31510819:1:3/filename=MobLand.S01E03.mkv&videoSize=3560556831&videoHash=1e89.json"
    )
    [track] = resp.json()["subtitles"]
    assert track["lang"] == "ron" and track["label"] == "Romanian (AI)"
    assert track["url"] == f"http://192.168.1.132:11471/srt/{IH}/0.srt"


def test_unknown_file_gets_no_track(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.get(f"/{TOKEN}/subtitles/movie/tt1/filename=Other.mkv.json").json() == {
        "subtitles": []
    }


def test_srt_serves_stored_cues_or_a_placeholder(tmp_path: Path) -> None:
    client, store = _client(tmp_path)
    assert "Se generează" in client.get(f"/srt/{IH}/0.srt").text
    store.save_chunk(IH, 0, 0, [Cue(1.0, 2.0, "Unu")])
    assert client.get(f"/srt/{IH}/0.srt").text == "1\n00:00:01,000 --> 00:00:02,000\nUnu\n"


def test_wrong_token_is_404(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.get("/" + "z" * 32 + "/manifest.json").status_code == 404
    assert client.get("/manifest.json").status_code == 404
