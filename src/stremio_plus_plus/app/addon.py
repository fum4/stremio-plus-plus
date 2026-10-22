"""Stremio addon endpoints.

`addon_router` (manifest, subtitle list) sits under the secret `/{token}` prefix and is the only
thing the public HTTPS listener serves. `lan_router` (generated SRT) is fetched by the streaming
server over the LAN, on the plain-http port only (https_guard.py).
"""

import asyncio
import secrets
from typing import Any
from urllib.parse import parse_qs

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from stremio_plus_plus.app.services import Services
from stremio_plus_plus.app.subtitle_switch import switch_on
from stremio_plus_plus.subtitles.constants import FIRST_ANSWER_WAIT_S, LABEL, LANG
from stremio_plus_plus.subtitles.cues import Cue, render_srt


def require_token(request: Request, token: str) -> None:
    if not secrets.compare_digest(token, services_of(request).env.addon_token):
        raise HTTPException(status_code=404)


log = structlog.get_logger()
HLS_START_WAIT_S = 3.0
addon_router = APIRouter(prefix="/{token}", dependencies=[Depends(require_token)])
lan_router = APIRouter()

MANIFEST: dict[str, Any] = {
    "id": "io.github.fum4.stremio-plus-plus",
    "version": "0.3.0",
    "name": "Stremio++",
    "description": (
        "Extras for the Stremio TV app, served from your Mac: the best release from your "
        "addons in one entry, with AI-generated Romanian subtitles (Whisper + Claude)."
    ),
    "resources": ["stream", "subtitles"],
    "types": ["movie", "series"],
    "idPrefixes": ["tt", "kitsu"],
    "catalogs": [],
}
PLACEHOLDER = [
    # Re-selecting the active track is a no-op on the TV: it has to be switched off and back on.
    Cue(
        0.0, 10.0, "Se generează subtitrarea… oprește subtitrarea și alege din nou „Romanian (AI)”."
    )
]


def services_of(request: Request) -> Services:
    return request.app.state.services


@addon_router.get("/manifest.json")
async def manifest() -> dict[str, Any]:
    return MANIFEST


@addon_router.get("/subtitles/{kind}/{item_id}/{extra}.json")
async def subtitles(request: Request, kind: str, item_id: str, extra: str) -> dict[str, Any]:
    services = services_of(request)
    params = {k: v[0] for k, v in parse_qs(extra).items()}
    filename, size = params.get("filename", ""), int(params.get("videoSize") or 0)
    for engine in (await services.server.engines()).values():
        for f in engine.files:
            if (filename and f.name.rsplit("/", 1)[-1] == filename) or (size and f.length == size):
                services.subtitles.ensure(engine.info_hash, f.index, f.name, f.length)
                return {"subtitles": [_entry(services, engine.info_hash, f.index)]}
    if (offer := services.picker.offered_for(item_id)) is not None:
        # Our own HLS entry (Stremio sends no file details for it): the menu entry is the
        # switch for the subtitles inside the stream (subtitle_switch.py).
        return {"subtitles": [_entry(services, *offer.file)]}
    return {"subtitles": []}


def _entry(services: Services, info_hash: str, file_index: int) -> dict[str, str]:
    base = f"http://{services.env.host_lan_ip}:{services.env.companion_port}"
    return {
        "id": f"companion-ro-{info_hash[:8]}-{file_index}",
        "lang": LANG,
        "label": LABEL,
        "url": f"{base}/srt/{info_hash}/{file_index}.srt",
    }


@lan_router.get("/srt/{info_hash}/{file_index}.srt", response_class=PlainTextResponse)
async def srt(request: Request, info_hash: str, file_index: int) -> PlainTextResponse:
    services = services_of(request)
    jobs = services.subtitles
    jobs.want(info_hash, file_index)
    session = services.sessions.playing(info_hash, file_index)
    waited = 0.0  # one budget for everything below: server.js gives up on us at ~10 s
    while session is None and services.picker.offered_file(info_hash, file_index):
        if waited >= HLS_START_WAIT_S:  # the viewer picked another source of the same file
            break
        await asyncio.sleep(0.5)  # remembered track fetched as our stream is still opening
        waited += 0.5
        session = services.sessions.playing(info_hash, file_index)
    if session is not None:
        return await switch_on(services, session, FIRST_ANSWER_WAIT_S - waited)
    cues = jobs.cues(info_hash, file_index)
    # The player fetches this once per track selection (and auto-selects a remembered language
    # as the episode loads): a few seconds' wait for the first window beats the placeholder.
    while not cues and jobs.generating(info_hash, file_index) and waited < FIRST_ANSWER_WAIT_S:
        await asyncio.sleep(0.5)
        waited += 0.5
        cues = jobs.cues(info_hash, file_index)
    log.info(
        "srt_served",
        info_hash=info_hash,
        file_index=file_index,
        cues=len(cues),
        until_s=round(cues[-1].end, 1) if cues else None,
        waited_s=waited,
    )
    return PlainTextResponse(
        render_srt(cues or PLACEHOLDER), media_type="application/x-subrip; charset=utf-8"
    )
