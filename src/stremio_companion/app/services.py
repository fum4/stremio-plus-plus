"""Long-lived dependencies, created once in the app lifespan and shared by routes and workers."""

import sqlite3
from dataclasses import dataclass

import httpx

from stremio_companion.config.env import Env
from stremio_companion.downloads.manager import DownloadManager
from stremio_companion.downloads.pins import Pinner
from stremio_companion.server.client import StremioServer
from stremio_companion.state.plays import Plays


@dataclass(frozen=True)
class Services:
    env: Env
    http: httpx.AsyncClient
    db: sqlite3.Connection
    server: StremioServer
    plays: Plays
    pinner: Pinner
    downloads: DownloadManager
