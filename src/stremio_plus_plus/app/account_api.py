"""`/api/account/*` (LAN only): connect the Stremio account, install Stremio++, keep it first.

The password is used for one login call and never stored or logged; only the authKey is kept
(account/credentials.py) and it's redacted from every log view.
"""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from stremio_plus_plus.account.api import StremioApiError
from stremio_plus_plus.app.admin import require_ui
from stremio_plus_plus.app.services import Services

router = APIRouter(prefix="/api/account", dependencies=[Depends(require_ui)])


def _services(request: Request) -> Services:
    return request.app.state.services


async def _view(services: Services, *, fresh: bool = False) -> dict[str, Any]:
    state = await services.account.state(fresh=fresh)
    return asdict(state) | {
        "keep_first": services.settings_file.settings.stremio.keep_addon_first,
        "manifest_url": services.host.manifest_url,
    }


def _fail(exc: StremioApiError) -> HTTPException:
    return HTTPException(status_code=401 if exc.code in {1, 2, 3} else 502, detail=str(exc))


@router.get("")
async def account(request: Request) -> dict[str, Any]:
    return await _view(_services(request))


class Login(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(request: Request, body: Login) -> dict[str, Any]:
    services = _services(request)
    try:
        await services.account.login(body.email, body.password)
    except StremioApiError as exc:
        raise _fail(exc) from None  # no chained context: it would carry the request
    return await _view(services)


class Key(BaseModel):
    auth_key: str


@router.post("/key")
async def use_key(request: Request, body: Key) -> dict[str, Any]:
    services = _services(request)
    try:
        await services.account.use_key(body.auth_key)
    except StremioApiError as exc:
        raise _fail(exc) from None
    return await _view(services)


@router.post("/logout")
async def logout(request: Request) -> dict[str, Any]:
    services = _services(request)
    services.account.disconnect()
    return await _view(services)


@router.post("/install")
async def install(request: Request) -> dict[str, Any]:
    services = _services(request)
    try:
        await services.account.install()
    except StremioApiError as exc:
        raise _fail(exc) from None
    return await _view(services)


@router.post("/keep")
async def keep_now(request: Request) -> dict[str, Any]:
    services = _services(request)
    try:
        await services.account.keep()
    except StremioApiError as exc:
        raise _fail(exc) from None
    return await _view(services, fresh=True)
