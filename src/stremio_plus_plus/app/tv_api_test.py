import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stremio_plus_plus.app import tv_api
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.app.services_test_support import make_services
from stremio_plus_plus.tls.stremio_cert import CERT_FILE
from stremio_plus_plus.tv.base import CodePrompt

UI = {"X-Stremio-Plus-Plus": "1", "Host": "192.168.1.132:11471"}
DOMAIN = "192-168-1-132.519b6502d940.stremio.rocks"


class FakeTv:
    def __init__(self, wants_code: bool = False) -> None:
        self.wants_code = wants_code
        self.typed: list[str] = []
        self.code: str | None = None
        self.paired = False

    async def pair(self, ask_code: CodePrompt) -> None:
        if self.wants_code:
            self.code = await ask_code()
        self.paired = True

    async def keys(self, *keys: str) -> None: ...

    async def text(self, text: str) -> None:
        self.typed.append(text)


def _client(tmp_path: Path, tv: FakeTv) -> tuple[TestClient, Services]:
    services = make_services(tmp_path, lambda r: httpx.Response(200, json={}))
    services.env.stremio_server_data_dir.mkdir()
    (services.env.stremio_server_data_dir / CERT_FILE).write_text(json.dumps({"domain": DOMAIN}))
    services.tv.remote = lambda: tv  # type: ignore[method-assign]
    app = FastAPI()
    app.include_router(tv_api.router)
    app.state.services = services
    return TestClient(app), services


def test_choosing_a_tv_writes_config_toml(tmp_path: Path) -> None:
    client, services = _client(tmp_path, FakeTv())
    state = client.put("/api/tv", json={"host": "192.168.1.134", "os": "samsung"}, headers=UI)
    assert state.json()["target"] == {"host": "192.168.1.134", "os": "samsung"}
    assert 'host = "192.168.1.134"' in services.settings_file.path.read_text()
    bad = client.put("/api/tv", json={"host": "192.168.1.134", "os": "roku"}, headers=UI)
    assert bad.status_code == 422


def test_pairing_with_a_code_from_the_ui(tmp_path: Path) -> None:
    tv = FakeTv(wants_code=True)
    client, services = _client(tmp_path, tv)
    client.put("/api/tv", json={"host": "192.168.1.135", "os": "androidtv"}, headers=UI)

    async def flow() -> None:
        services.tv.start_pairing()
        for _ in range(50):
            if services.tv.pairing.state == "code":
                break
            await asyncio.sleep(0.01)
        assert services.tv.submit_code(" 4F2A9C ")
        for _ in range(50):
            if services.tv.pairing.state == "paired":
                break
            await asyncio.sleep(0.01)

    asyncio.run(flow())
    assert tv.code == "4F2A9C" and services.tv.pairing.state == "paired"


def test_type_it_for_me_types_the_right_url(tmp_path: Path) -> None:
    tv = FakeTv()
    client, _ = _client(tmp_path, tv)
    client.put("/api/tv", json={"host": "192.168.1.134", "os": "samsung"}, headers=UI)
    assert client.post("/api/tv/type", json={"which": "server"}, headers=UI).json() == {"ok": True}
    assert client.post("/api/tv/type", json={"which": "revert"}, headers=UI).json() == {"ok": True}
    assert tv.typed == [f"https://{DOMAIN}:12470", "http://127.0.0.1:11470"]


def test_driving_stremio_needs_a_recorded_sequence(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, FakeTv())
    client.put("/api/tv", json={"host": "192.168.1.134", "os": "samsung"}, headers=UI)
    resp = client.post("/api/tv/apply", json={"which": "server"}, headers=UI)
    assert resp.status_code == 502 and "Type it for me" in resp.json()["detail"]


@pytest.mark.parametrize("path", ["/api/tv", "/api/tv/discover"])
def test_requires_the_ui_header(tmp_path: Path, path: str) -> None:
    client, _ = _client(tmp_path, FakeTv())
    assert client.request("GET" if path == "/api/tv" else "POST", path).status_code == 403
