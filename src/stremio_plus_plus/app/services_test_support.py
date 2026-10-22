"""A Services wired to fakes (a mocked server.js, a temp db and config dir) for route tests."""

from collections.abc import Callable
from ipaddress import IPv4Address
from pathlib import Path

import httpx
from pydantic import AnyHttpUrl

from stremio_plus_plus.account.api import StremioApi
from stremio_plus_plus.account.credentials import AuthFile
from stremio_plus_plus.account.service import StremioAccount
from stremio_plus_plus.app.picker import Picker
from stremio_plus_plus.app.services import HostInfo, Services
from stremio_plus_plus.app.tv_service import TvService
from stremio_plus_plus.config.env import Env
from stremio_plus_plus.config.settings_file import SettingsFile
from stremio_plus_plus.downloads.manager import DownloadManager
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.log.hub import HUB
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.activity import ActivityStore
from stremio_plus_plus.state.db import open_db
from stremio_plus_plus.state.plays import Plays
from stremio_plus_plus.stream.sessions import Sessions
from stremio_plus_plus.subtitles.cues import Cue
from stremio_plus_plus.subtitles.jobs import SubtitleJobs
from stremio_plus_plus.subtitles.model_cache import ModelDownload
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.subtitles.translators.registry import ConfiguredTranslator
from stremio_plus_plus.tls.addon import AddonTls
from stremio_plus_plus.watch.clients import ClientMonitor

TOKEN = "k" * 32
DOMAIN = "192-168-1-132.519b6502d940.stremio.rocks"
TLS = AddonTls("stremio", DOMAIN, Path("cert.pem"), Path("key.pem"))


class NoStt:
    async def transcribe(self, audio: object, offset_s: float) -> list[Cue]:
        raise AssertionError("not used in route tests")


def make_services(tmp_path: Path, handler: Callable[[httpx.Request], httpx.Response]) -> Services:
    env = Env(
        stremio_server_url=AnyHttpUrl("http://srv:11470"),
        stremio_server_log=tmp_path / "server.log",
        companion_log=tmp_path / "companion.log",
        companion_host="0.0.0.0",
        companion_port=11471,
        companion_data_dir=tmp_path,
        stremio_server_data_dir=tmp_path / "server",
        stremio_server_settings=tmp_path / "server-settings.json",
        config_dir=tmp_path / "config",
        ui_dir=tmp_path / "ui",
        host_lan_ip=IPv4Address("192.168.1.132"),
        tv_host=None,  # a fresh install: the TV comes from config.toml via the setup
        tv_os=None,
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
    account = StremioAccount(
        StremioApi(http, "https://api.test"),
        AuthFile(tmp_path),
        "io.github.fum4.stremio-plus-plus",
        {"id": "io.github.fum4.stremio-plus-plus"},
        lambda: None,
        lambda: True,
        HUB.add_secret,  # as in factory.py: the key is redacted from every log view
    )
    return Services(
        env=env,
        host=HostInfo(IPv4Address("192.168.1.132"), TOKEN, 8443, tls=TLS),
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
        picker=Picker(http, server, account.collection),
        sessions=Sessions(tmp_path / "hls"),
        playback_handlers=[],
        model_download=ModelDownload(),
        clients=ClientMonitor(tmp_path),
        activity=ActivityStore(db),
        account=account,
        tv=TvService(env, settings_file),
    )
