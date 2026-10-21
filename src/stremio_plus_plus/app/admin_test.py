from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stremio_plus_plus.app import admin
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.app.services_test_support import TOKEN, make_services

UI = {"X-Stremio-Plus-Plus": "1", "Host": "192.168.1.132:11471"}
STATS = {"ab" * 20: {"name": "Movie", "files": [{"name": "m.mkv", "length": 10}]}}


def _client(tmp_path: Path) -> tuple[TestClient, Services]:
    services = make_services(tmp_path, lambda r: httpx.Response(200, json=STATS))
    app = FastAPI()
    app.include_router(admin.router)
    app.state.services = services
    return TestClient(app), services


def test_calls_without_the_ui_header_or_from_a_foreign_host_are_refused(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.get("/api/settings", headers={"Host": "192.168.1.132"}).status_code == 403
    rebound = UI | {"Host": "evil.example.com"}
    assert client.get("/api/settings", headers=rebound).status_code == 403
    assert client.get("/api/settings", headers=UI | {"Host": "batman.local:11471"}).is_success


def test_settings_round_trip_through_the_file(tmp_path: Path) -> None:
    client, services = _client(tmp_path)
    body = {"subtitles": {"translator": {"model": "claude-sonnet-5-5"}}}
    resp = client.put("/api/settings", json=body, headers=UI)
    assert resp.json()["settings"]["subtitles"]["translator"]["model"] == "claude-sonnet-5-5"
    assert 'model = "claude-sonnet-5-5"' in services.settings_file.path.read_text()
    bad = {"downloads": {"min_free_gb": 0}}
    assert client.put("/api/settings", json=bad, headers=UI).status_code == 422


def test_secrets_are_write_only(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    resp = client.put("/api/secrets/anthropic_api_key", json={"value": "sk-ant-x"}, headers=UI)
    assert resp.json()["secrets"] == {"anthropic_api_key": True}
    assert "sk-ant-x" not in resp.text
    assert client.put("/api/secrets/nope", json={"value": "x"}, headers=UI).status_code == 404


def test_providers_say_what_is_missing(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    by_id = {p["id"]: p for p in client.get("/api/providers", headers=UI).json()}
    assert by_id["anthropic"]["ready"] is False and by_id["anthropic"]["why"] == "add an API key"
    assert by_id["claude-cli"]["models"][0]["id"] == "claude-haiku-5-5"


def test_translator_test_reports_a_config_error(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    resp = client.post("/api/translator/test", json={"provider": "anthropic"}, headers=UI)
    assert resp.json() == {"ok": False, "error": "no Anthropic API key set"}
    resp = client.post("/api/translator/test", json={"provider": "claude-cli"}, headers=UI)
    assert resp.json()["error"].startswith("claude CLI not found")


def test_status_includes_torrents_and_the_install_url(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    status = client.get("/api/status", headers=UI).json()
    assert status["server"]["ok"] and status["torrents"][0]["name"] == "Movie"
    assert status["addon"]["manifest_url"].endswith(f"/{TOKEN}/manifest.json")
    assert status["translator"]["provider"] == "claude-cli"
