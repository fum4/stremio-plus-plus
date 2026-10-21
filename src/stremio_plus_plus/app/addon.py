"""Stremio addon endpoints.

`addon_router` (manifest, subtitle list) sits under the secret `/{token}` prefix and is the only
thing the public HTTPS listener serves. `lan_router` (generated SRT) is fetched by the streaming
server over the LAN, on the plain-http port only (https_guard.py).
"""

import secrets
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from stremio_plus_plus.app.services import Services
from stremio_plus_plus.subtitles.constants import LABEL, LANG
from stremio_plus_plus.subtitles.cues import Cue, render_srt


def _require_token(request: Request, token: str) -> None:
    if not secrets.compare_digest(token, _services(request).env.addon_token):
        raise HTTPException(status_code=404)


addon_router = APIRouter(prefix="/{token}", dependencies=[Depends(_require_token)])
lan_router = APIRouter()

MANIFEST: dict[str, Any] = {
    "id": "io.github.fum4.stremio-plus-plus",
    "version": "0.1.0",
    "name": LABEL,
    "description": "AI-generated Romanian subtitles (Whisper + Claude), from stremio++",
    "resources": ["subtitles"],
    "types": ["movie", "series"],
    "idPrefixes": ["tt", "kitsu"],
    "catalogs": [],
}
PLACEHOLDER = [
    Cue(0.0, 8.0, "Se generează subtitrarea… reselectează „Romanian (AI)” peste 1-2 minute.")
]


def _services(request: Request) -> Services:
    return request.app.state.services


@addon_router.get("/manifest.json")
async def manifest() -> dict[str, Any]:
    return MANIFEST


@addon_router.get("/subtitles/{kind}/{item_id}/{extra}.json")
async def subtitles(request: Request, kind: str, item_id: str, extra: str) -> dict[str, Any]:
    services = _services(request)
    params = {k: v[0] for k, v in parse_qs(extra).items()}
    filename, size = params.get("filename", ""), int(params.get("videoSize") or 0)
    for engine in (await services.server.engines()).values():
        for f in engine.files:
            if (filename and f.name.rsplit("/", 1)[-1] == filename) or (size and f.length == size):
                services.subtitles.ensure(engine.info_hash, f.index, f.name, f.length)
                base = f"http://{services.env.host_lan_ip}:{services.env.companion_port}"
                return {
                    "subtitles": [
                        {
                            "id": f"companion-ro-{engine.info_hash[:8]}-{f.index}",
                            "lang": LANG,
                            "label": LABEL,
                            "url": f"{base}/srt/{engine.info_hash}/{f.index}.srt",
                        }
                    ]
                }
    return {"subtitles": []}


@lan_router.get("/srt/{info_hash}/{file_index}.srt", response_class=PlainTextResponse)
async def srt(request: Request, info_hash: str, file_index: int) -> PlainTextResponse:
    cues = _services(request).subtitle_store.cues(info_hash, file_index)
    return PlainTextResponse(
        render_srt(cues or PLACEHOLDER), media_type="application/x-subrip; charset=utf-8"
    )
