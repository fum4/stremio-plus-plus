"""Long-lived dependencies, created once in the app lifespan and shared by routes and workers."""

import sqlite3
from dataclasses import dataclass

import httpx

from stremio_plus_plus.config.env import Env
from stremio_plus_plus.downloads.manager import DownloadManager
from stremio_plus_plus.downloads.pins import Pinner
from stremio_plus_plus.server.client import StremioServer
from stremio_plus_plus.state.plays import Plays
from stremio_plus_plus.subtitles.jobs import SubtitleJobs
from stremio_plus_plus.subtitles.store import SubtitleStore


@dataclass(frozen=True)
class Services:
    env: Env
    http: httpx.AsyncClient
    db: sqlite3.Connection
    server: StremioServer
    plays: Plays
    pinner: Pinner
    downloads: DownloadManager
    subtitle_store: SubtitleStore
    subtitles: SubtitleJobs
