"""The TV as the setup sees it: which one, is it paired, pair it from the UI, drive Stremio on it.

Pairing runs in the background: Samsung/LG wait for "Allow" on the TV, Android TV asks for the
code the TV shows, which the UI posts back (`submit_code`).
"""

import asyncio
from dataclasses import dataclass
from ipaddress import IPv4Address
from typing import Literal

import structlog

from stremio_plus_plus.config.env import Env
from stremio_plus_plus.config.host import tv_target
from stremio_plus_plus.config.settings import TvOs
from stremio_plus_plus.config.settings_file import SettingsFile
from stremio_plus_plus.tv import macros
from stremio_plus_plus.tv.base import TvControlError, TvRemote
from stremio_plus_plus.tv.factory import make_remote

log = structlog.get_logger()
PairState = Literal["idle", "waiting", "code", "paired", "failed"]
CODE_TIMEOUT_S = 120.0


@dataclass
class Pairing:
    state: PairState = "idle"
    error: str | None = None


class TvService:
    def __init__(self, env: Env, settings_file: SettingsFile) -> None:
        self._env = env
        self._settings_file = settings_file
        self.pairing = Pairing()
        self._code: asyncio.Future[str] | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def target(self) -> tuple[IPv4Address, TvOs] | None:
        return tv_target(self._env, self._settings_file.settings)

    @property
    def pinned_by_env(self) -> bool:
        return bool(self._env.tv_host and self._env.tv_os)

    def remote(self) -> TvRemote:
        return make_remote(self.target, self._env.companion_data_dir)

    @property
    def paired(self) -> bool:
        try:
            return self.remote().paired
        except TvControlError:
            return False

    def start_pairing(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self.pairing = Pairing("waiting")
        self._task = asyncio.create_task(self._pair(), name="tv-pair")

    def submit_code(self, code: str) -> bool:
        if self._code is None or self._code.done():
            return False
        self._code.set_result(code.strip())
        return True

    async def _ask_code(self) -> str:
        self._code = asyncio.get_running_loop().create_future()
        self.pairing = Pairing("code")
        return await asyncio.wait_for(self._code, CODE_TIMEOUT_S)

    async def _pair(self) -> None:
        try:
            await self.remote().pair(self._ask_code)
            self.pairing = Pairing("paired")
            log.info("tv_paired", target=str(self.target))
        except (TvControlError, OSError, TimeoutError) as exc:
            self.pairing = Pairing("failed", str(exc) or type(exc).__name__)
            log.warning("tv_pair_failed", error=self.pairing.error)

    async def type_url(self, url: str) -> None:
        await self.remote().text(url)

    def can_drive(self) -> bool:
        target = self.target
        return target is not None and macros.available(target[1])

    async def set_server_url(self, url: str) -> None:
        target = self.target
        if target is None or not macros.available(target[1]):
            raise TvControlError("no recorded key sequence for this TV yet: use Type it for me")
        await macros.run(self.remote(), macros.SET_SERVER_URL[target[1]], url)
