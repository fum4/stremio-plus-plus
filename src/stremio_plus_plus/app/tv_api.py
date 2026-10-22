"""`/api/tv/*` (LAN only): find the TV, pair it, and set Stremio's server URL on it."""

from dataclasses import asdict
from ipaddress import IPv4Address
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from stremio_plus_plus.app.admin import require_ui
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.app.setup import REVERT_URL, tv_server_url
from stremio_plus_plus.config.settings import TvOs
from stremio_plus_plus.config.settings_file import SettingsError
from stremio_plus_plus.tv.base import TvControlError
from stremio_plus_plus.tv.discover import discover

router = APIRouter(prefix="/api/tv", dependencies=[Depends(require_ui)])
Which = Literal["server", "revert"]


def _services(request: Request) -> Services:
    return request.app.state.services


def _url(services: Services, which: Which) -> str:
    if which == "revert":
        return REVERT_URL
    url = tv_server_url(services)
    if url is None:
        raise HTTPException(status_code=409, detail="set up the streaming server first")
    return url


@router.get("")
async def tv_state(request: Request) -> dict[str, Any]:
    services = _services(request)
    tv = services.tv
    target = tv.target
    return {
        "target": {"host": str(target[0]), "os": target[1]} if target else None,
        "pinned_by_env": tv.pinned_by_env,
        "paired": tv.paired,
        "pairing": asdict(tv.pairing),
        "can_drive": tv.can_drive(),
        "client_last_seen": services.clients.last_seen,
    }


@router.post("/discover")
async def find_tvs() -> list[dict[str, Any]]:
    return [asdict(tv) | {"host": str(tv.host)} for tv in await discover()]


class TvChoice(BaseModel):
    host: IPv4Address
    os: TvOs


@router.put("")
async def choose_tv(request: Request, choice: TvChoice) -> dict[str, Any]:
    services = _services(request)
    if services.tv.pinned_by_env:
        raise HTTPException(status_code=409, detail="TV_HOST/TV_OS in .env.local pin the TV")
    try:
        services.settings_file.save({"tv": {"host": str(choice.host), "os": choice.os}})
    except SettingsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await tv_state(request)


@router.post("/pair")
async def pair(request: Request) -> dict[str, Any]:
    services = _services(request)
    if services.tv.target is None:
        raise HTTPException(status_code=409, detail="choose a TV first")
    services.tv.start_pairing()
    return await tv_state(request)


class Code(BaseModel):
    code: str


@router.post("/pair/code")
async def pair_code(request: Request, body: Code) -> dict[str, Any]:
    if not _services(request).tv.submit_code(body.code):
        raise HTTPException(status_code=409, detail="the TV isn't asking for a code")
    return await tv_state(request)


class Target(BaseModel):
    which: Which


@router.post("/type")
async def type_url(request: Request, body: Target) -> dict[str, bool]:
    """Type the URL into whatever field is focused on the TV."""
    services = _services(request)
    try:
        await services.tv.type_url(_url(services, body.which))
    except (TvControlError, OSError) as exc:
        raise HTTPException(status_code=502, detail=f"the TV didn't take it: {exc}") from exc
    return {"ok": True}


@router.post("/apply")
async def apply(request: Request, body: Target) -> dict[str, bool]:
    """Open Stremio's server URL setting on the TV and enter the URL (recorded key sequence)."""
    services = _services(request)
    try:
        await services.tv.set_server_url(_url(services, body.which))
    except (TvControlError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ok": True}
