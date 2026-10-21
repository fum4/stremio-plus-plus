"""Amazon Fire TV adapter (Fire OS): ADB over the network, on adb-shell (Apache-2.0).

NOT verified on a real TV: only the hermetic tests in firetv_test.py. Fire TV has no Android TV
Remote v2 service, so this needs Settings → My Fire TV → Developer options → ADB debugging ON.
Pairing: this host's RSA key (FIRETV_KEY_FILE, mode 600) is offered on port 5555 and the TV asks
"Allow USB debugging?"; tick "Always allow from this computer". Keys/text are `input keyevent` /
`input text` shell commands. Vega OS Fire TVs (not Android) have no ADB and are not covered.
"""

# adb-shell ships no type information; keep its untyped surface inside this module.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

import asyncio
import re
import shlex
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

from adb_shell.adb_device_async import AdbDeviceTcpAsync
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_cryptography import CryptographySigner
from adb_shell.exceptions import AdbConnectionError, AdbTimeoutError, DeviceAuthError

from stremio_plus_plus.tv.base import CodePrompt, TvControlError, TvRefusedError
from stremio_plus_plus.tv.constants import (
    CONNECT_TIMEOUT_S,
    FIRETV_PORT,
    KEY_DELAY_S,
    PAIR_TIMEOUT_S,
)
from stremio_plus_plus.tv.credentials import private_umask, remove, restrict
from stremio_plus_plus.tv.keys import ANDROID, native_keys

_NATIVE_KEY = re.compile(r"^(KEYCODE_[A-Z0-9_]+|[0-9]{1,3})$")


def keyevent_command(key: str) -> str:
    """`input keyevent` for one key; refuses anything that is not a key name (shell safety)."""
    if not _NATIVE_KEY.fullmatch(key):
        raise TvControlError(f"not an Android key name: {key!r} (e.g. KEYCODE_HOME, or 3)")
    return f"input keyevent {key}"


def text_command(text: str) -> str:
    """`input text` for printable ASCII; `input text` spells a space as %s."""
    if not text.isascii() or not text.isprintable():
        raise TvControlError("Fire TV `input text` only types printable ASCII")
    return f"input text {shlex.quote(text.replace(' ', '%s'))}"


class AdbDeviceLike(Protocol):
    """The part of adb_shell's AdbDeviceTcpAsync this adapter uses (a seam for the tests)."""

    async def connect(self, rsa_keys: list[object], auth_timeout_s: float) -> bool: ...
    async def shell(self, command: str) -> str: ...
    async def close(self) -> None: ...


DeviceFactory = Callable[[str, int], AdbDeviceLike]


def _tcp_device(host: str, port: int) -> AdbDeviceLike:
    device = AdbDeviceTcpAsync(host, port, default_transport_timeout_s=CONNECT_TIMEOUT_S)
    return device  # pyright: ignore[reportReturnType]  (untyped library)


class FireTvRemote:
    def __init__(
        self, host: str, key_path: Path, device_factory: DeviceFactory = _tcp_device
    ) -> None:
        self._host = host
        self._key_path = key_path
        self._pub_path = key_path.with_name(key_path.name + ".pub")
        self._device_factory = device_factory

    @property
    def paired(self) -> bool:
        return self._key_path.is_file()

    async def pair(self, ask_code: CodePrompt) -> None:
        del ask_code  # Fire TV confirms with "Allow USB debugging?" on screen, no code
        new_key = not self.paired
        if new_key:
            self._key_path.parent.mkdir(parents=True, exist_ok=True)
            with private_umask():
                keygen(str(self._key_path))
            restrict(self._key_path, self._pub_path)
        try:
            async with self._session(PAIR_TIMEOUT_S):
                pass
        except BaseException:
            if new_key:  # the TV never accepted it; an older, accepted key stays
                remove(self._key_path, self._pub_path)
            raise

    async def keys(self, *keys: str) -> None:
        commands = [keyevent_command(k) for k in native_keys(keys, ANDROID, "firetv")]
        async with self._session(CONNECT_TIMEOUT_S) as device:
            for command in commands:
                await device.shell(command)
                await asyncio.sleep(KEY_DELAY_S)

    async def text(self, text: str) -> None:
        command = text_command(text)
        async with self._session(CONNECT_TIMEOUT_S) as device:
            await device.shell(command)

    @asynccontextmanager
    async def _session(self, auth_timeout_s: float) -> AsyncGenerator[AdbDeviceLike]:
        if not self.paired:
            raise TvRefusedError("not paired: mise run tv -- pair")
        signer = CryptographySigner(str(self._key_path))
        device = self._device_factory(self._host, FIRETV_PORT)
        try:
            await device.connect(rsa_keys=[signer], auth_timeout_s=auth_timeout_s)
            yield device
        except DeviceAuthError as exc:
            raise TvRefusedError(f"the TV did not allow this host: {exc}") from exc
        except (AdbConnectionError, AdbTimeoutError, TimeoutError) as exc:
            raise TvControlError(f"no ADB on the TV (ADB debugging off?): {exc}") from exc
        finally:
            await device.close()
