import stat
from pathlib import Path
from typing import Any

import pytest
from aiowebostv import endpoints as ep
from aiowebostv.exceptions import WebOsTvPairError

from stremio_plus_plus.tv.base import TvRefusedError
from stremio_plus_plus.tv.webos import WebOsClientLike, WebOsRemote


class FakeClient:
    def __init__(self, host: str, client_key: str | None, *, issue: str = "k-1") -> None:
        self.host = host
        self.client_key = client_key
        self._issue = issue
        self.sent: list[tuple[str, Any]] = []
        self.connected = False
        self.refuse = False

    async def connect(self) -> bool:
        if self.refuse:
            raise WebOsTvPairError("denied")
        self.client_key = self.client_key or self._issue
        self.connected = True
        return True

    async def disconnect(self) -> None:
        self.connected = False

    async def button(self, name: str) -> None:
        self.sent.append(("button", name))

    async def request(self, uri: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.sent.append((uri, payload))
        return {"returnValue": True}


async def _no_code() -> str:
    raise AssertionError("webOS never asks for a code")


def _remote(tmp_path: Path, fake: list[FakeClient], **kw: Any) -> WebOsRemote:
    def factory(host: str, key: str | None) -> WebOsClientLike:
        client = FakeClient(host, key, **kw)
        fake.append(client)
        return client

    return WebOsRemote("10.0.0.5", tmp_path / "tv-webos-client-key", factory)


@pytest.mark.asyncio
async def test_pair_stores_the_client_key_mode_600_and_reuses_it(tmp_path: Path) -> None:
    clients: list[FakeClient] = []
    remote = _remote(tmp_path, clients)
    assert not remote.paired
    await remote.pair(_no_code)
    key_file = tmp_path / "tv-webos-client-key"
    assert key_file.read_text() == "k-1"
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
    await remote.keys("HOME")
    assert clients[1].client_key == "k-1"
    assert not clients[1].connected


@pytest.mark.asyncio
async def test_keys_and_text_map_to_buttons_and_ime_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("stremio_plus_plus.tv.webos.KEY_DELAY_S", 0)
    clients: list[FakeClient] = []
    remote = _remote(tmp_path, clients)
    await remote.keys("HOME", "FAST_FORWARD", "NETFLIX")
    assert clients[0].sent == [("button", "HOME"), ("button", "FASTFORWARD"), ("button", "NETFLIX")]
    await remote.text("https://ă b")
    assert clients[1].sent == [
        (ep.INSERT_TEXT, {"text": "https://ă b", "replace": 0}),
        (ep.SEND_ENTER, None),
    ]


@pytest.mark.asyncio
async def test_a_refused_prompt_is_a_refusal(tmp_path: Path) -> None:
    def factory(host: str, key: str | None) -> WebOsClientLike:
        client = FakeClient(host, key)
        client.refuse = True
        return client

    remote = WebOsRemote("10.0.0.5", tmp_path / "k", factory)
    with pytest.raises(TvRefusedError):
        await remote.pair(_no_code)
    assert not remote.paired
