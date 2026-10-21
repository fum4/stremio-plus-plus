"""The admin UI's JSON API (`/api/*`), LAN-only: the public HTTPS listener 404s it (https_guard.py).

Every call needs the `X-Stremio-Plus-Plus` header and a LAN Host: the custom header forces a CORS
preflight that the companion refuses, and the Host check stops DNS rebinding, so a web page open in
a LAN browser can neither read (the addon URL holds the token) nor write. Secrets are write-only:
the API says whether one is set, never what it is.
"""

import time
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from stremio_plus_plus.app.services import Services
from stremio_plus_plus.config.settings import TranslatorSettings
from stremio_plus_plus.config.settings_file import SettingsError
from stremio_plus_plus.downloads.disk import free_bytes
from stremio_plus_plus.subtitles.translators.base import TranslatorConfigError
from stremio_plus_plus.subtitles.translators.registry import PROVIDERS

SAMPLE = [
    "Where the hell have you been?",
    "I told you, I was at my sister's.",
    "Don't lie to me. Not tonight.",
    "We need to leave. Now.",
]


def _services(request: Request) -> Services:
    return request.app.state.services


def _require_ui(request: Request, x_stremio_plus_plus: str | None = Header(default=None)) -> None:
    if x_stremio_plus_plus != "1":
        raise HTTPException(status_code=403, detail="missing X-Stremio-Plus-Plus header")
    env = _services(request).env
    host = (request.headers.get("host") or "").rsplit(":", 1)[0]
    if host not in {str(env.host_lan_ip), "localhost", "127.0.0.1"} and not host.endswith(".local"):
        raise HTTPException(status_code=403, detail=f"open the UI via the LAN address, not {host}")


router = APIRouter(prefix="/api", dependencies=[Depends(_require_ui)])


def _settings_view(services: Services) -> dict[str, Any]:
    f = services.settings_file
    return {
        "settings": f.settings.model_dump(),
        "version": f.version,
        "path": str(f.path),
        "error": f.error,
        "secrets": {name: value is not None for name, value in f.secrets.model_dump().items()},
    }


@router.get("/settings")
async def get_settings(request: Request) -> dict[str, Any]:
    return _settings_view(_services(request))


@router.put("/settings")
async def put_settings(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    services = _services(request)
    try:
        services.settings_file.save(body)
    except SettingsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _settings_view(services)


class SecretBody(BaseModel):
    value: str | None


@router.put("/secrets/{name}")
async def put_secret(request: Request, name: str, body: SecretBody) -> dict[str, Any]:
    services = _services(request)
    try:
        services.settings_file.set_secret(name, (body.value or "").strip() or None)
    except SettingsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _settings_view(services)


@router.get("/providers")
async def providers(request: Request) -> list[dict[str, Any]]:
    services = _services(request)
    secrets = services.settings_file.secrets.model_dump()
    out: list[dict[str, Any]] = []
    for info in PROVIDERS.values():
        ready, why = True, None
        if info.secret and not secrets.get(info.secret):
            ready, why = False, "add an API key"
        elif info.id == "claude-cli" and not services.env.claude_cli.is_file():
            ready, why = False, f"claude CLI not found at {services.env.claude_cli}"
        out.append(asdict(info) | {"ready": ready, "why": why})
    return out


@router.post("/translator/test")
async def test_translator(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    """Translate a few sample lines with the given (possibly unsaved) translator settings."""
    services = _services(request)
    try:
        settings = TranslatorSettings.model_validate(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if services.translator.cap_reached:
        return {"ok": False, "error": "the hourly call cap is reached; try again later"}
    translator = services.translator.build_test(settings, services.settings_file.secrets)
    t0 = time.monotonic()
    try:
        out = await translator.translate(SAMPLE, [])
    except TranslatorConfigError as exc:
        return {"ok": False, "error": str(exc)}
    ok = out != SAMPLE
    return {
        "ok": ok,
        "error": None if ok else "the model's reply was unusable",
        "seconds": round(time.monotonic() - t0, 2),
        "lines": [{"source": s, "target": t} for s, t in zip(SAMPLE, out, strict=True)],
    }


@router.get("/status")
async def status(request: Request) -> dict[str, Any]:
    services = _services(request)
    env, settings = services.env, services.settings_file.settings
    try:
        engines = list((await services.server.engines()).values())
        server_ok = True
    except Exception:  # the status page must render even with the server down
        engines, server_ok = [], False
    pinned = services.pinner.pinned()
    translator = services.translator
    return {
        "server": {"ok": server_ok, "url": env.server_base},
        "torrents": [
            {
                "info_hash": e.info_hash,
                "name": e.name,
                "size": sum(f.length for f in e.files),
                "downloaded": e.downloaded,
                "speed": e.download_speed,
                "peers": e.peers,
                "pinned": any(ih == e.info_hash for ih, _ in pinned),
            }
            for e in engines
        ],
        "subtitles": [asdict(j) for j in services.subtitles.progress()],
        "translator": {
            "provider": settings.subtitles.translator.provider,
            "model": settings.subtitles.translator.model,
            "calls_last_hour": translator.calls_last_hour,
            "cap": settings.subtitles.translator.max_calls_per_hour,
            "calls": translator.stats.calls,
            "failures": translator.stats.failures,
            "last_latency_s": translator.stats.last_latency_s,
            "last_error": translator.stats.last_error,
        },
        "disk": {
            "free": free_bytes(services.cache_dir),
            "reserve": settings.downloads.min_free_bytes,
        },
        "addon": {
            "manifest_url": (
                f"https://{env.addon_domain}:{env.addon_https_port}/{env.addon_token}/manifest.json"
            ),
        },
        "settings_version": services.settings_file.version,
    }
