"""Pins the Samsung wire behaviour (verified on the owner's TV) through a fake connection."""

import json
import stat
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest

from stremio_plus_plus.tv import samsung
from stremio_plus_plus.tv.base import TvRefusedError
from stremio_plus_plus.tv.samsung import SamsungRemote


class FakeWs:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.sent: list[str] = []

    async def recv(self) -> str:
        return self.events.pop(0)

    async def send(self, message: str) -> None:
        self.sent.append(message)


@pytest.fixture
def tv(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"events": [], "urls": [], "ws": []}

    @asynccontextmanager
    async def connect(url: str, **_: object) -> AsyncGenerator[FakeWs]:
        state["urls"].append(url)
        ws = FakeWs(list(state["events"]))
        state["ws"].append(ws)
        yield ws

    monkeypatch.setattr(samsung, "connect", connect)
    monkeypatch.setattr(samsung, "KEY_DELAY_S", 0)
    return state


async def _no_code() -> str:
    raise AssertionError("Samsung never asks for a code")


TOUCH = '{"event": "ms.remote.touchDisable"}'


@pytest.mark.asyncio
async def test_pair_saves_the_token_and_later_sessions_send_it(
    tv: dict[str, Any], tmp_path: Path
) -> None:
    tv["events"] = [TOUCH, '{"event": "ms.channel.connect", "data": {"token": "777"}}']
    remote = SamsungRemote("192.168.1.134", tmp_path / "tv-token")
    await remote.pair(_no_code)
    assert (tmp_path / "tv-token").read_text() == "777"
    assert stat.S_IMODE((tmp_path / "tv-token").stat().st_mode) == 0o600
    assert "token" not in tv["urls"][0]
    tv["events"] = ['{"event": "ms.channel.connect", "data": {}}']
    await remote.keys("KEY_HOME", "DOWN", "BACK")
    assert tv["urls"][1].endswith("&token=777")
    sent = [json.loads(m) for m in tv["ws"][1].sent]
    assert [m["params"]["DataOfCmd"] for m in sent] == ["KEY_HOME", "KEY_DOWN", "KEY_RETURN"]
    assert tv["ws"][1].sent[0] == (
        '{"method": "ms.remote.control", "params": {"Cmd": "Click", "DataOfCmd": "KEY_HOME", '
        '"Option": "false", "TypeOfRemote": "SendRemoteKey"}}'
    )


@pytest.mark.asyncio
async def test_refusal(tv: dict[str, Any], tmp_path: Path) -> None:
    tv["events"] = ['{"event": "ms.channel.unauthorized"}']
    with pytest.raises(TvRefusedError):
        await SamsungRemote("tv", tmp_path / "tv-token").pair(_no_code)
