"""The user's Stremio account, as stremio++ uses it: connect (password → authKey, or a pasted
authKey for Google/Facebook sign-ins), install Stremio++ in one click, and keep it first.

The keeper re-checks every few minutes: installing another addon reorders the collection, and a
new addon URL (e.g. after switching to the zero-config certificate) has to reach the account too.
It never adds Stremio++ by itself (removing it is the user's call) and never touches other addons.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from stremio_plus_plus.account.api import StremioApi, StremioApiError
from stremio_plus_plus.account.collection import (
    Addon,
    addon_id,
    addon_name,
    descriptor,
    ours_first,
    position,
)
from stremio_plus_plus.account.credentials import AuthFile

log = structlog.get_logger()
KEEP_EVERY_S = 10 * 60
FIRST_CHECK_AFTER_S = 30.0
STATE_TTL_S = 20.0


@dataclass(frozen=True)
class AddonSummary:
    id: str | None
    name: str
    ours: bool


@dataclass
class AccountState:
    connected: bool  # a key is stored and Stremio hasn't signed it out (it may be unreachable)
    email: str | None = None
    error: str | None = None
    position: int | None = None  # of Stremio++ in the collection; None = not installed
    url_current: bool = False  # the installed entry points at this host's current addon URL
    addons: list[AddonSummary] = field(default_factory=list[AddonSummary])


class StremioAccount:
    def __init__(
        self,
        api: StremioApi,
        auth: AuthFile,
        our_id: str,
        manifest: dict[str, Any],
        manifest_url: Callable[[], str | None],
        keep_first: Callable[[], bool],
        on_key: Callable[[str], None] = lambda _key: None,  # e.g. the log hub's redaction
    ) -> None:
        self._api = api
        self._auth = auth
        self._our_id = our_id
        self._manifest = manifest
        self._manifest_url = manifest_url
        self._keep_first = keep_first
        self._on_key = on_key
        self._cache: tuple[float, AccountState] | None = None
        self._lock = asyncio.Lock()  # install and keep are read-modify-write on the collection
        if key := auth.load():
            on_key(key)

    @property
    def key(self) -> str | None:
        return self._auth.load()

    async def login(self, email: str, password: str) -> AccountState:
        self._remember(await self._api.login(email.strip(), password))
        log.info("stremio_account_connected", method="password")
        return await self.state(fresh=True)

    async def use_key(self, auth_key: str) -> AccountState:
        auth_key = auth_key.strip().strip('"')
        await self._api.email(auth_key)  # rejects a wrong or expired key before it's stored
        self._remember(auth_key)
        log.info("stremio_account_connected", method="auth_key")
        return await self.state(fresh=True)

    def disconnect(self) -> None:
        """Forget the key here. No API logout: other tools on this host may share the session."""
        self._auth.clear()
        self._cache = None
        log.info("stremio_account_disconnected")

    def _remember(self, auth_key: str) -> None:
        self._on_key(auth_key)
        self._auth.save(auth_key)
        self._cache = None

    async def state(self, *, fresh: bool = False) -> AccountState:
        if not fresh and self._cache and time.monotonic() - self._cache[0] < STATE_TTL_S:
            return self._cache[1]
        key = self.key
        if key is None:
            return AccountState(connected=False)
        try:
            email = await self._api.email(key)
            addons = await self._api.addons(key)
        except StremioApiError as exc:
            message = (
                "Stremio signed this login out: connect again" if exc.session_gone else str(exc)
            )
            return AccountState(connected=not exc.session_gone, error=message)
        state = self._summarize(email, addons)
        self._cache = (time.monotonic(), state)
        return state

    def _summarize(self, email: str | None, addons: list[Addon]) -> AccountState:
        at = position(addons, self._our_id)
        url = self._manifest_url()
        current = at is not None and url is not None and addons[at].get("transportUrl") == url
        summaries = [
            AddonSummary(
                addon_id(a),
                addon_name(a),
                addon_id(a) == self._our_id,
            )
            for a in addons
        ]
        return AccountState(True, email, None, at, current, summaries)

    async def install(self) -> AccountState:
        """Add Stremio++ (or repoint it at this host's URL) and put it first."""
        key, url = self.key, self._manifest_url()
        if key is None:
            raise StremioApiError("connect your Stremio account first")
        if url is None:
            raise StremioApiError("the addon has no HTTPS address yet: finish the server step")
        async with self._lock:
            addons = await self._api.addons(key)
            _refuse_empty(addons)
            await self._api.set_addons(
                key, ours_first(addons, self._our_id, descriptor(url, self._manifest))
            )
        log.info("stremio_addon_installed", position=0)
        return await self.state(fresh=True)

    async def keep(self, *, force: bool = False) -> bool:
        """Put Stremio++ back first / on the current URL if it's installed. True if changed.
        `force`: a click on "Move to the top", which doesn't depend on the keep-first setting."""
        key, url = self.key, self._manifest_url()
        if key is None or not (force or self._keep_first()):
            return False
        async with self._lock:
            return await self._keep(key, url)

    async def _keep(self, key: str, url: str | None) -> bool:
        addons = await self._api.addons(key)
        at = position(addons, self._our_id)
        if at is None:
            return False  # not installed: the user's call, not ours
        stale_url = url is not None and addons[at].get("transportUrl") != url
        if at == 0 and not stale_url:
            return False
        replacement = descriptor(url, self._manifest) if stale_url and url else None
        _refuse_empty(addons)
        await self._api.set_addons(key, ours_first(addons, self._our_id, replacement))
        self._cache = None
        log.info("stremio_addon_kept_first", was_at=at, repointed=stale_url)
        return True

    async def run(self) -> None:
        await asyncio.sleep(FIRST_CHECK_AFTER_S)
        while True:
            try:
                await self.keep()
            except StremioApiError as exc:
                log.warning("stremio_addon_keep_failed", error=str(exc))
            except Exception:  # never let the keeper die; no secrets in scope here
                log.exception("stremio_addon_keep_crashed")
            await asyncio.sleep(KEEP_EVERY_S)


def _refuse_empty(addons: list[Addon]) -> None:
    """A real account always has Stremio's own addons: an empty list is a bad read, and writing
    a list built on it would wipe the collection."""
    if not addons:
        raise StremioApiError("Stremio returned no addons; nothing was changed")
