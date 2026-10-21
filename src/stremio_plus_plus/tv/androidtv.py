"""Android TV / Google TV adapter (Android TV Remote protocol v2), on androidtvremote2 (Apache-2.0).

NOT verified on a real TV: only the hermetic tests in androidtv_test.py. Covers Sony, Philips,
TCL, Hisense (Android/Google TV models), Nvidia Shield, Chromecast with Google TV: anything
running the preinstalled "Android TV Remote Service". Not Fire TV (see firetv.py).

Pairing: TLS to port 6467 with a self-signed client certificate; the TV shows a 6-hex-digit
code, which the person types into `mise run tv -- pair`. The certificate + key (mode 600) are
the credential; they are deleted again if pairing fails, so `paired` means a finished pairing.
Remote: TLS to 6466, protobuf key events; text goes through the remote's IME channel.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

from androidtvremote2 import AndroidTVRemote, CannotConnect, ConnectionClosed, InvalidAuth

from stremio_plus_plus.tv.base import CodePrompt, TvControlError, TvRefusedError
from stremio_plus_plus.tv.constants import CLIENT_NAME, KEY_DELAY_S
from stremio_plus_plus.tv.credentials import private_umask, remove, restrict
from stremio_plus_plus.tv.keys import ANDROID, native_keys


class AndroidTvClientLike(Protocol):
    """The part of androidtvremote2.AndroidTVRemote this adapter uses (a seam for the tests)."""

    async def async_generate_cert_if_missing(self) -> bool: ...
    async def async_start_pairing(self) -> None: ...
    async def async_finish_pairing(self, pairing_code: str) -> None: ...
    async def async_connect(self) -> None: ...
    def send_key_command(self, key_code: int | str, direction: int | str = ...) -> None: ...
    def send_text(self, text: str) -> None: ...
    def disconnect(self) -> None: ...


# (client name, certfile, keyfile, host) -> client
ClientFactory = Callable[[str, str, str, str], AndroidTvClientLike]


def normalize_code(code: str) -> str:
    """The TV shows the code in upper-case hex; accept it typed loosely."""
    return code.strip().replace(" ", "").upper()


class AndroidTvRemote:
    def __init__(
        self,
        host: str,
        cert_path: Path,
        key_path: Path,
        client_factory: ClientFactory = AndroidTVRemote,
    ) -> None:
        self._host = host
        self._cert_path = cert_path
        self._key_path = key_path
        self._client_factory = client_factory

    @property
    def paired(self) -> bool:
        return self._cert_path.is_file() and self._key_path.is_file()

    async def pair(self, ask_code: CodePrompt) -> None:
        client = self._client()
        self._cert_path.parent.mkdir(parents=True, exist_ok=True)
        generated = False
        try:
            with private_umask():
                generated = await client.async_generate_cert_if_missing()
            restrict(self._cert_path, self._key_path)
            await client.async_start_pairing()
            await client.async_finish_pairing(normalize_code(await ask_code()))
        except (InvalidAuth, CannotConnect, ConnectionClosed) as exc:
            if generated:  # the TV never accepted it; an older, accepted cert stays
                remove(self._cert_path, self._key_path)
            raise _translate(exc) from exc
        except BaseException:  # cancelled, Ctrl-C at the code prompt…: no half-made pairing
            if generated:
                remove(self._cert_path, self._key_path)
            raise
        finally:
            client.disconnect()

    async def keys(self, *keys: str) -> None:
        names = native_keys(keys, ANDROID, "androidtv")
        async with self._session() as client:
            for name in names:
                client.send_key_command(name)
                await asyncio.sleep(KEY_DELAY_S)  # sends are buffered; also paces the UI

    async def text(self, text: str) -> None:
        async with self._session() as client:
            client.send_text(text)
            await asyncio.sleep(KEY_DELAY_S)

    def _client(self) -> AndroidTvClientLike:
        return self._client_factory(
            CLIENT_NAME, str(self._cert_path), str(self._key_path), self._host
        )

    @asynccontextmanager
    async def _session(self) -> AsyncGenerator[AndroidTvClientLike]:
        if not self.paired:
            raise TvRefusedError("not paired: mise run tv -- pair")
        client = self._client()
        try:
            await client.async_connect()
            yield client
        except (InvalidAuth, CannotConnect, ConnectionClosed, ValueError) as exc:
            raise _translate(exc) from exc
        finally:
            client.disconnect()


def _translate(exc: Exception) -> TvControlError:
    if isinstance(exc, InvalidAuth):
        return TvRefusedError(f"the TV rejected this host (wrong code, or pair again): {exc}")
    if isinstance(exc, (CannotConnect, ConnectionClosed)):
        return TvControlError(f"TV unreachable or closed the connection: {exc}")
    if isinstance(exc, ValueError):
        return TvControlError(f"unknown Android TV key: {exc}")
    return TvControlError(str(exc))
