import json
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stremio_plus_plus.app import account_api
from stremio_plus_plus.app.services_test_support import make_services
from stremio_plus_plus.log.hub import HUB

UI = {"X-Stremio-Plus-Plus": "1", "Host": "192.168.1.132:11471"}


def _handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content or b"{}")
    method = request.url.path.rsplit("/", 1)[-1]
    if method == "login":
        if body.get("password") != "hunter2-correct":
            return httpx.Response(200, json={"error": {"code": 3, "message": "Wrong passphrase"}})
        return httpx.Response(200, json={"result": {"authKey": "secret-auth-key-123"}})
    if method == "getUser":
        return httpx.Response(200, json={"result": {"email": "me@example.com"}})
    if method == "addonCollectionGet":
        return httpx.Response(200, json={"result": {"addons": []}})
    return httpx.Response(200, json={})


def _client(tmp_path: Path) -> TestClient:
    services = make_services(tmp_path, _handler)
    app = FastAPI()
    app.include_router(account_api.router)
    app.state.services = services
    return TestClient(app)


def test_wrong_password_is_a_401_and_the_password_goes_nowhere(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post(
        "/api/account/login",
        json={"email": "me@example.com", "password": "hunter2-wrong"},
        headers=UI,
    )
    assert resp.status_code == 401 and resp.json()["detail"] == "Wrong passphrase"
    assert not (tmp_path / "stremio-auth.json").exists()


def test_login_keeps_only_the_key_and_never_shows_it(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = client.post(
        "/api/account/login",
        json={"email": "me@example.com", "password": "hunter2-correct"},
        headers=UI,
    )
    assert resp.json()["connected"] and resp.json()["email"] == "me@example.com"
    assert "secret-auth-key-123" not in resp.text and "hunter2" not in resp.text
    stored = (tmp_path / "stremio-auth.json").read_text()
    assert "hunter2" not in stored
    logged = " ".join(f"{e.text} {e.fields}" for e in HUB.since(0, 100_000))
    assert "hunter2" not in logged
    assert HUB.redact("key=secret-auth-key-123") == "key=[redacted]"
