"""A Services wired to fakes (a mocked server.js, a temp db and config dir) for route tests."""

from collections.abc import Callable
from ipaddress import IPv4Address
from pathlib import Path

import httpx
from pydantic import AnyHttpUrl

from stremio_plus_plus.app.picker import Picker
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.config.env import Env
from stremio_plus_plus.config.settings_file import SettingsFile
from stremio_plus_plus.downloads.manager import DownloadManager
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.state.plays import Plays
from stremio_plus_plus.stream.sessions import Sessions
from stremio_plus_plus.subtitles.cues import Cue
from stremio_plus_plus.subtitles.jobs import SubtitleJobs
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.subtitles.translators.registry import ConfiguredTranslator

TOKEN = "k" * 32


class NoStt:
    async def transcribe(self, audio: object, offset_s: float) -> list[Cue]:
        raise AssertionError("not used in route tests")


def make_services(tmp_path: Path, handler: Callable[[httpx.Request], httpx.Response]) -> Services:
    env = Env(
        stremio_server_url=AnyHttpUrl("http://srv:11470"),
        stremio_server_log=tmp_path / "server.log",
        companion_host="0.0.0.0",
        companion_port=11471,
        companion_data_dir=tmp_path,
        config_dir=tmp_path / "config",
        ui_dir=tmp_path / "ui",
        host_lan_ip=IPv4Address("192.168.1.132"),
        tv_host=IPv4Address("192.168.1.134"),
        tv_os="samsung",
        addon_domain="stremio.nomadware.io",
        addon_https_port=8443,
        addon_token=TOKEN,
        claude_cli=tmp_path / "claude-missing",
        log_level="INFO",
        log_format="json",
    )
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    server = StremioServer("http://srv:11470", http)
    db = open_db(tmp_path / "s.db")
    store = SubtitleStore(db)
    pinner = Pinner(http, server)
    settings_file = SettingsFile(env.config_dir)
    translator = ConfiguredTranslator(settings_file, env.claude_cli)
    return Services(
        env=env,
        settings_file=settings_file,
        http=http,
        db=db,
        server=server,
        cache_dir=tmp_path,
        plays=Plays(db),
        pinner=pinner,
        downloads=DownloadManager(server, pinner, lambda: 0, lambda: 0),
        subtitle_store=store,
        subtitles=SubtitleJobs(server, store, NoStt(), translator),
        translator=translator,
        picker=Picker(http, server, tmp_path),
        sessions=Sessions(tmp_path / "hls"),
        playback_handlers=[],
    )
