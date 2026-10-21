import json
from pathlib import Path

from stremio_plus_plus.log.hub import LogHub, seed


def test_redacts_the_auth_key_api_keys_and_registered_secrets() -> None:
    hub = LogHub()
    hub.add_secret("k" * 32)
    hub.server_line("-> GET /get-https?ipAddress=1.2.3.4&authKey=abc123def")
    hub.companion_event(
        {"event": "x", "url": f"https://h/{'k' * 32}/manifest.json", "key": "sk-ant-api03-zz"}
    )
    server, companion = hub.since(0, 10)
    assert "abc123def" not in server.text and "authKey=[redacted]" in server.text
    assert "k" * 32 not in str(companion.fields) and "zz" not in str(companion.fields)


def test_since_and_listeners() -> None:
    hub = LogHub(max_entries=3)
    seen: list[str] = []
    hub.listeners.append(lambda e: seen.append(e.text))
    for i in range(5):
        hub.server_line(f"line {i}")
    assert [e.text for e in hub.since(0, 10)] == ["line 2", "line 3", "line 4"]
    assert [e.text for e in hub.since(4, 10)] == ["line 4"]
    assert len(seen) == 5


def test_seed_reads_history_without_notifying(tmp_path: Path) -> None:
    (tmp_path / "server.log").write_text("-> GET /settings\nEngine created for " + "a" * 40 + "\n")
    event = {"event": "subtitle_window", "level": "info", "timestamp": "2026-10-21T11:26:23Z"}
    (tmp_path / "companion.log").write_text(json.dumps(event) + "\nnot json\n")
    hub = LogHub()
    seen: list[object] = []
    hub.listeners.append(seen.append)
    seed(hub, tmp_path / "server.log", tmp_path / "companion.log")
    entries = hub.since(0, 10)
    assert [e.source for e in entries] == ["companion", "server", "server"]
    assert entries[0].ts == 1792581983.0 and entries[1].ts is None
    assert seen == []
