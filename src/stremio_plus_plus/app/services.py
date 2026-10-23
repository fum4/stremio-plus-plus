"""Long-lived dependencies, created once in the app lifespan and shared by routes and workers."""

import sqlite3
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
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
from stremio_plus_plus.subtitles.store import SubtitleStore
from stremio_plus_plus.subtitles.translators.registry import ConfiguredTranslator
from stremio_plus_plus.watch.events import Event


@dataclass(frozen=True)
class Services:
    env: Env
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
