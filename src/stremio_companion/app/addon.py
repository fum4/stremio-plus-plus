"""Stremio addon endpoints: manifest, subtitle list, generated SRT."""

from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from stremio_companion.app.services import Services
from stremio_companion.subtitles.constants import LABEL, LANG
from stremio_companion.subtitles.cues import Cue, render_srt

router = APIRouter()

MANIFEST: dict[str, Any] = {
    "id": "io.github.fum4.stremio-companion",
    "version": "0.1.0",
    "name": LABEL,
    "description": "AI-generated Romanian subtitles (Whisper + Claude), from stremio-companion",
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


@router.get("/manifest.json")
async def manifest() -> dict[str, Any]:
    return MANIFEST


@router.get("/subtitles/{kind}/{item_id}/{extra}.json")
async def subtitles(request: Request, kind: str, item_id: str, extra: str) -> dict[str, Any]:
    services = _services(request)
    params = {k: v[0] for k, v in parse_qs(extra).items()}
    filename, size = params.get("filename", ""), int(params.get("videoSize") or 0)
    for engine in (await services.server.engines()).values():
        for f in engine.files:
            if (filename and f.name.rsplit("/", 1)[-1] == filename) or (size and f.length == size):
                services.subtitles.ensure(
                    engine.info_hash, f.index, f.name, f.length, params.get("videoHash")
                )
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


@router.get("/srt/{info_hash}/{file_index}.srt", response_class=PlainTextResponse)
async def srt(request: Request, info_hash: str, file_index: int) -> PlainTextResponse:
    cues = _services(request).subtitle_store.cues(info_hash, file_index)
    return PlainTextResponse(
        render_srt(cues or PLACEHOLDER), media_type="application/x-subrip; charset=utf-8"
    )
