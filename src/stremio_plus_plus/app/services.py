"""Long-lived dependencies, created once in the app lifespan and shared by routes and workers."""

import sqlite3
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from ipaddress import IPv4Address
from pathlib import Path

import httpx

from stremio_plus_plus.app.picker import Picker
from stremio_plus_plus.config.env import Env
from stremio_plus_plus.config.settings_file import SettingsFile
from stremio_plus_plus.downloads.manager import DownloadManager
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.plays import Plays
from stremio_plus_plus.stream.sessions import Sessions
from stremio_plus_plus.subtitles.jobs import SubtitleJobs
from stremio_plus_plus.subtitles.model_cache import ModelDownload
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.subtitles.translators.registry import ConfiguredTranslator
from stremio_plus_plus.tls.addon import AddonTls
from stremio_plus_plus.watch.events import Event


@dataclass
class HostInfo:
    """Resolved at boot (config/host.py); `tls` is filled in and renewed by boot's supervisor."""

    lan_ip: IPv4Address
    addon_token: str
    https_port: int
    tls: AddonTls | None = None

    @property
    def addon_base(self) -> str | None:
        """`https://<name>:<port>/<token>`: what every public addon URL starts with."""
        if self.tls is None:
            return None
        return f"https://{self.tls.domain}:{self.https_port}/{self.addon_token}"

    @property
    def manifest_url(self) -> str | None:
        return f"{self.addon_base}/manifest.json" if self.addon_base else None


@dataclass(frozen=True)
class Services:
    env: Env
    host: HostInfo
    settings_file: SettingsFile
    http: httpx.AsyncClient
    db: sqlite3.Connection
    server: StremioServer
    cache_dir: Path
    plays: Plays
    pinner: Pinner
    downloads: DownloadManager
    subtitle_store: SubtitleStore
    subtitles: SubtitleJobs
    picker: Picker
    sessions: Sessions
    # What the log tracker feeds; HLS playback is reported to the same handlers directly.
    playback_handlers: Sequence[Callable[[Event], Awaitable[None]]]
    translator: ConfiguredTranslator
    model_download: ModelDownload
