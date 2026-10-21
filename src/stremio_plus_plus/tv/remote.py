"""Control the TV from the host: pair once (an "Allow" prompt on the TV), then send keys/text."""

import asyncio
import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from websockets.asyncio.client import ClientConnection, connect

from stremio_plus_plus.tv.constants import CLIENT_NAME, KEY_DELAY_S, PAIR_TIMEOUT_S, WS_PORT
from stremio_plus_plus.tv.protocol import (
    Connected,
    Refused,
    channel_url,
    key_message,
    parse_event,
    text_messages,
)


class TvRefusedError(Exception):
    """The TV denied the pairing, or nobody pressed Allow in time."""


class TvRemote:
    def __init__(self, host: str, token_path: Path) -> None:
        self._host = host
        self._token_path = token_path

    @property
    def paired(self) -> bool:
        return self._token_path.is_file()

    async def pair(self) -> None:
        """Connect, waiting up to a minute for Allow on the TV; the token is stored (mode 600)."""
        async with self._session():
            pass

    async def keys(self, *keys: str) -> None:
        async with self._session() as ws:
            for key in keys:
                await ws.send(key_message(key))
                await asyncio.sleep(KEY_DELAY_S)

    async def text(self, text: str) -> None:
        async with self._session() as ws:
            for message in text_messages(text):
                await ws.send(message)
                await asyncio.sleep(KEY_DELAY_S)

    @asynccontextmanager
    async def _session(self) -> AsyncGenerator[ClientConnection]:
        token = self._token_path.read_text().strip() if self.paired else None
        tls = ssl.create_default_context()
        tls.check_hostname = False
        tls.verify_mode = ssl.CERT_NONE  # the TV's certificate is self-signed
        url = channel_url(self._host, WS_PORT, CLIENT_NAME, token)
        async with connect(url, ssl=tls, open_timeout=10) as ws:
            await self._await_connect(ws)
            yield ws

    async def _await_connect(self, ws: ClientConnection) -> None:
        try:
            async with asyncio.timeout(PAIR_TIMEOUT_S):
                while True:
                    event = parse_event(str(await ws.recv()))
                    if isinstance(event, Refused):
                        raise TvRefusedError("pairing refused on the TV")
                    if isinstance(event, Connected):
                        if event.token:
                            self._save_token(event.token)
                        return
        except TimeoutError as exc:
            raise TvRefusedError("no Allow on the TV within a minute") from exc

    def _save_token(self, token: str) -> None:
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(token)
        self._token_path.chmod(0o600)
