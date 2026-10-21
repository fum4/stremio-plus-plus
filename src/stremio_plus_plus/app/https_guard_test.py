import pytest
from starlette.types import Message, Receive, Scope, Send

from stremio_plus_plus.app.https_guard import HttpsGuard

TOKEN = "t" * 32


async def _inner(scope: Scope, receive: Receive, send: Send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


async def _status(port: int, path: str) -> int:
    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    async def receive() -> Message:
        return {"type": "http.request"}

    scope: Scope = {"type": "http", "path": path, "server": ("0.0.0.0", port)}
    await HttpsGuard(_inner, https_port=8443, token=TOKEN)(scope, receive, send)
    return int(sent[0]["status"])


@pytest.mark.asyncio
async def test_https_listener_serves_only_token_paths() -> None:
    assert await _status(8443, f"/{TOKEN}/manifest.json") == 200
    assert await _status(8443, "/health") == 404
    assert await _status(8443, "/srt/aa/0.srt") == 404
    assert await _status(8443, "/manifest.json") == 404


@pytest.mark.asyncio
async def test_lan_listener_is_untouched() -> None:
    assert await _status(11471, "/srt/aa/0.srt") == 200
    assert await _status(11471, "/health") == 200
