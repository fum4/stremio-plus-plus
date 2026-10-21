import json
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stremio_plus_plus.app import setup
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.app.services_test_support import make_services
from stremio_plus_plus.tls.stremio_cert import CERT_FILE

UI = {"X-Stremio-Plus-Plus": "1", "Host": "192.168.1.132:11471"}
SERVER_DOMAIN = "192-168-1-132.519b6502d940.stremio.rocks"


class FakeServer:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {"cacheRoot": "/tmp/cache", "remoteHttps": ""}
        self.posted: list[dict[str, Any]] = []
        self.https_requests: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/settings" and request.method == "POST":
            body = json.loads(request.content)
            self.posted.append(body)
            self.values |= body
            return httpx.Response(200, json={"success": True})
        if request.url.path == "/settings":
            return httpx.Response(200, json={"values": self.values})
        if request.url.path == "/get-https":
            self.https_requests.append(str(request.url.params["ipAddress"]))
            return httpx.Response(200, json={"domain": SERVER_DOMAIN, "port": 12470})
        return httpx.Response(200, json={})


def _client(tmp_path: Path) -> tuple[TestClient, Services, FakeServer]:
    fake = FakeServer()
    services = make_services(tmp_path, fake)
    services.env.stremio_server_settings.write_text(json.dumps({"cacheSize": 4398046511104}))
    services.env.stremio_server_data_dir.mkdir()
    (services.env.stremio_server_data_dir / CERT_FILE).write_text(
        json.dumps({"domain": SERVER_DOMAIN, "cert": "C", "key": "K", "notAfter": "2026-12-24"})
    )
    app = FastAPI()
    app.include_router(setup.router)
    app.state.services = services
    return TestClient(app), services, fake


def _check(state: dict[str, Any], id_: str) -> dict[str, Any]:
    return next(c for c in state["checks"] if c["id"] == id_)


def test_fresh_state_lists_what_to_do(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path)
    state = client.get("/api/setup", headers=UI).json()
    assert state["completed"] is False
    assert _check(state, "server")["level"] == "ok"
    assert _check(state, "server_tv")["fix"] == "configure_server"
    assert state["tv"] == {
        "server_url": f"https://{SERVER_DOMAIN}:12470",
        "revert_url": "http://127.0.0.1:11470",
    }
    assert state["addon_url"].endswith("/manifest.json")


def test_configure_server_merges_the_settings_and_points_https_at_the_lan_ip(
    tmp_path: Path,
) -> None:
    client, _, fake = _client(tmp_path)
    state = client.post("/api/setup/server", headers=UI).json()
    assert fake.posted == [{"cacheSize": 4398046511104, "remoteHttps": "192.168.1.132"}]
    assert fake.https_requests == ["192.168.1.132"]
    assert _check(state, "server_tv")["level"] == "ok"


def test_never_sends_a_zero_cache(tmp_path: Path) -> None:
    client, services, fake = _client(tmp_path)
    services.env.stremio_server_settings.write_text(json.dumps({"cacheSize": 0}))
    assert client.post("/api/setup/server", headers=UI).status_code == 422
    assert fake.posted == []


def test_complete_is_remembered(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path)
    assert client.post("/api/setup/complete", headers=UI).json()["completed"] is True
    assert client.get("/api/setup", headers=UI).json()["completed"] is True
