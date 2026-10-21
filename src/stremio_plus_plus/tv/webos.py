"""LG webOS adapter (SSAP), on aiowebostv (Home Assistant's webOS client, Apache-2.0).

NOT verified on a real TV: only the hermetic tests in webos_test.py. Pairing shows an "Allow this
device?" prompt on the TV; the TV answers with a client key, stored at WEBOS_KEY_FILE (mode 600).
Keys go over the pointer input socket (`type:button`), text through the IME service
(`com.webos.service.ime/insertText` then `sendEnterKey`), which needs a focused text field.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Protocol

import aiohttp
from aiowebostv import WebOsClient, webos_client
from aiowebostv import endpoints as ep
from aiowebostv.exceptions import WebOsTvError, WebOsTvPairError

from stremio_plus_plus.tv.base import CodePrompt, TvControlError, TvRefusedError
from stremio_plus_plus.tv.constants import KEY_DELAY_S, PAIR_TIMEOUT_S
from stremio_plus_plus.tv.credentials import write_secret
from stremio_plus_plus.tv.keys import WEBOS, native_keys


class WebOsClientLike(Protocol):
    """The part of aiowebostv.WebOsClient this adapter uses (a seam for the tests)."""

    client_key: str | None

    async def connect(self) -> bool: ...
    async def disconnect(self) -> None: ...
    async def button(self, name: str) -> None: ...
    async def request(self, uri: str, payload: dict[str, Any] | None = None) -> dict[str, Any]: ...


ClientFactory = Callable[[str, str | None], WebOsClientLike]


def insert_text_payload(text: str) -> dict[str, Any]:
    return {"text": text, "replace": 0}


class WebOsRemote:
    def __init__(
        self, host: str, key_path: Path, client_factory: ClientFactory = WebOsClient
    ) -> None:
        self._host = host
        self._key_path = key_path
        self._client_factory = client_factory

    @property
    def paired(self) -> bool:
        return self._key_path.is_file()

    async def pair(self, ask_code: CodePrompt) -> None:
        del ask_code  # webOS confirms with a prompt on the TV, no code
        # aiowebostv waits only 10 s for the prompt to be answered; give a person time to walk over.
        # The library reads this module global at call time.
        webos_client.RECEIVE_TIMEOUT = int(PAIR_TIMEOUT_S)
        async with self._session():
            pass

    async def keys(self, *keys: str) -> None:
        names = native_keys(keys, WEBOS, "webos")
        async with self._session() as client:
            for name in names:
                await client.button(name)
                await asyncio.sleep(KEY_DELAY_S)

    async def text(self, text: str) -> None:
        async with self._session() as client:
            await client.request(ep.INSERT_TEXT, insert_text_payload(text))
            await asyncio.sleep(KEY_DELAY_S)
            await client.request(ep.SEND_ENTER)

    @asynccontextmanager
    async def _session(self) -> AsyncGenerator[WebOsClientLike]:
        key = self._key_path.read_text().strip() if self.paired else None
        client = self._client_factory(self._host, key)
        try:
            await client.connect()
            if client.client_key and client.client_key != key:
                write_secret(self._key_path, client.client_key)
            yield client
        except WebOsTvPairError as exc:
            raise TvRefusedError(f"pairing refused on the TV: {exc}") from exc
        except TimeoutError as exc:
            raise TvRefusedError("the TV did not answer (pairing prompt not accepted?)") from exc
        except (WebOsTvError, aiohttp.ClientError) as exc:
            raise TvControlError(str(exc)) from exc
        finally:
            await client.disconnect()
