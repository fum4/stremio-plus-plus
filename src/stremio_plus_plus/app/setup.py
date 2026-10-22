"""First-run setup (`/api/setup/*`, LAN only like the rest of the admin API).

Checks what a working host needs, and fixes what the companion can fix by itself: the streaming
server's settings (incl. remoteHttps so the TV can reach it) and the Whisper model download.
What only a person can do (the TV's server URL, installing the addon) is shown, then confirmed.
"""

import json
import platform
import shutil
import time
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from stremio_plus_plus.app.admin import provider_status, require_ui
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.downloads.disk import free_bytes
from stremio_plus_plus.server.constants import HTTPS_PORT
from stremio_plus_plus.subtitles.model_cache import is_cached
from stremio_plus_plus.tls.stremio_cert import server_domain

log = structlog.get_logger()
router = APIRouter(prefix="/api/setup", dependencies=[Depends(require_ui)])
Level = Literal["ok", "warn", "bad"]
MARKER = "setup-complete"
GB = 1024**3
DISK_OK, DISK_MIN = 50 * GB, 10 * GB
REVERT_URL = "http://127.0.0.1:11470"  # the TV's own server: playback without this host


def _services(request: Request) -> Services:
    return request.app.state.services


def tv_server_url(services: Services) -> str | None:
    """What the TV's Stremio server URL must be: this host's server over its stremio.rocks name."""
    domain = server_domain(services.env.stremio_server_data_dir)
    return f"https://{domain}:{HTTPS_PORT}" if domain else None


def _check(
    id_: str, label: str, level: Level, detail: str, fix: str | None = None
) -> dict[str, Any]:
    return {"id": id_, "label": label, "level": level, "detail": detail, "fix": fix}


async def _server_values(services: Services) -> dict[str, Any] | None:
    try:
        return await services.server.settings()
    except Exception:  # down or not started yet: reported as a check, not an error
        return None


async def _checks(services: Services) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    apple = platform.system() == "Darwin" and platform.machine() == "arm64"
    out.append(
        _check(
            "mac",
            "Apple Silicon Mac",
            "ok" if apple else "bad",
            f"{platform.system()} {platform.machine()}",
            None if apple else "Whisper on MLX needs an M-series Mac",
        )
    )
    missing = [b for b in ("ffmpeg", "ffprobe") if shutil.which(b) is None]
    out.append(
        _check(
            "tools",
            "Audio tools",
            "bad" if missing else "ok",
            f"missing: {', '.join(missing)}" if missing else "ffmpeg and ffprobe found",
            "brew install ffmpeg" if missing else None,
        )
    )
    values = await _server_values(services)
    out.append(
        _check(
            "server",
            "Streaming server",
            "ok" if values else "bad",
            services.env.server_base if values else "not responding",
            None if values else "mise run services:install server",
        )
    )
    lan_ip = str(services.host.lan_ip)
    tv_ready = values is not None and values.get("remoteHttps") == lan_ip
    out.append(
        _check(
            "server_tv",
            "Server reachable by the TV",
            "ok" if tv_ready else "warn",
            f"HTTPS for {lan_ip}" if tv_ready else "not set up for the TV yet",
            None if tv_ready else "configure_server",
        )
    )
    tls = services.host.tls
    out.append(
        _check(
            "https",
            "Addon over HTTPS",
            "ok" if tls else "warn",
            f"{tls.domain} ({tls.mode})" if tls else "waiting for a certificate",
            None if tls else "configure_server",
        )
    )
    ready = [
        p
        for p in provider_status(services)
        if p["id"] == services.settings_file.settings.subtitles.translator.provider
    ]
    translator_ok = bool(ready and ready[0]["ready"])
    out.append(
        _check(
            "translator",
            "Translator",
            "ok" if translator_ok else "warn",
            ready[0]["label"] if translator_ok else (ready[0]["why"] if ready else "unknown"),
            None if translator_ok else "subtitles",
        )
    )
    model = services.settings_file.settings.subtitles.speech.model
    cached = is_cached(model)
    out.append(
        _check(
            "model",
            "Speech model",
            "ok" if cached else "warn",
            model if cached else "not downloaded yet",
            None if cached else "download_model",
        )
    )
    seen = services.clients.last_seen
    out.append(
        _check(
            "tv_connected",
            "TV connected",
            "ok" if seen and tv_ready else "warn",
            "a Stremio app is using this server" if seen and tv_ready else "waiting for the TV",
            None,
        )
    )
    free = free_bytes(services.cache_dir)
    level: Level = "ok" if free >= DISK_OK else "warn" if free >= DISK_MIN else "bad"
    out.append(
        _check(
            "disk",
            "Free disk space",
            level,
            f"{free / GB:.0f} GB free",
            None if level == "ok" else "films are cached whole: 50 GB or more is comfortable",
        )
    )
    return out


@router.get("")
async def setup_state(request: Request) -> dict[str, Any]:
    services = _services(request)
    marker = services.env.companion_data_dir / MARKER
    return {
        "completed": marker.exists(),
        "checks": await _checks(services),
        "lan_ip": str(services.host.lan_ip),
        "tv": {
            "server_url": tv_server_url(services),
            "revert_url": REVERT_URL,
        },
        "addon_url": services.host.manifest_url,
        "model": services.model_download.view()
        if services.model_download.model
        else {"model": services.settings_file.settings.subtitles.speech.model, "state": "idle"},
    }


@router.post("/server")
async def configure_server(request: Request) -> dict[str, Any]:
    """Apply the repo's server settings + remoteHttps = this host's LAN IP, then get the cert."""
    services = _services(request)
    lan_ip = str(services.host.lan_ip)
    values: dict[str, Any] = json.loads(services.env.stremio_server_settings.read_text())
    if not values.get("cacheSize"):  # 0 = a 45 MB RAM ring buffer that stops while paused
        raise HTTPException(status_code=422, detail="refusing cacheSize 0 (docs: § Cache)")
    try:
        await services.server.update_settings(values | {"remoteHttps": lan_ip})
        await services.server.request_https(lan_ip)
    except Exception as exc:
        log.warning("setup_server_configure_failed", error=str(exc))
        raise HTTPException(status_code=502, detail=f"the streaming server said no: {exc}") from exc
    log.info("setup_server_configured", remote_https=lan_ip)
    return await setup_state(request)


@router.post("/model")
async def download_model(request: Request) -> dict[str, Any]:
    services = _services(request)
    services.model_download.start(services.settings_file.settings.subtitles.speech.model)
    return services.model_download.view()


@router.get("/model")
async def model_progress(request: Request) -> dict[str, Any]:
    services = _services(request)
    return services.model_download.view()


@router.post("/complete")
async def complete(request: Request) -> dict[str, Any]:
    services = _services(request)
    (services.env.companion_data_dir / MARKER).write_text(str(time.time()))
    log.info("setup_completed")
    return await setup_state(request)
