from pathlib import Path

import pytest
from pydantic import ValidationError

from stremio_plus_plus.config.env import load_env

VALID = {
    "STREMIO_SERVER_URL": "http://127.0.0.1:11470",
    "STREMIO_SERVER_LOG": "~/Library/Logs/stremio-plus-plus/server.log",
    "COMPANION_HOST": "0.0.0.0",
    "COMPANION_PORT": "11471",
    "COMPANION_DATA_DIR": "/tmp/companion-data",
    "HOST_LAN_IP": "192.168.1.132",
    "TV_HOST": "192.168.1.134",
    "TV_OS": "samsung",
    "CLAUDE_CLI": "~/.local/bin/claude",
    "ADDON_DOMAIN": "stremio.nomadware.io",
    "ADDON_HTTPS_PORT": "8443",
    "ADDON_TOKEN": "x" * 32,
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "json",
}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for key in VALID:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def _set_all(env: pytest.MonkeyPatch, **overrides: str) -> None:
    for key, value in (VALID | overrides).items():
        env.setenv(key, value)


def test_loads_a_complete_environment(env: pytest.MonkeyPatch) -> None:
    _set_all(env)
    loaded = load_env()
    assert loaded.companion_port == 11471
    assert loaded.server_base == "http://127.0.0.1:11470"
    assert str(loaded.host_lan_ip) == "192.168.1.132"


def test_expands_home_in_paths(env: pytest.MonkeyPatch) -> None:
    _set_all(env)
    assert (
        load_env().stremio_server_log == Path.home() / "Library/Logs/stremio-plus-plus/server.log"
    )


@pytest.mark.parametrize("missing", sorted(VALID))
def test_fails_on_any_missing_value(env: pytest.MonkeyPatch, missing: str) -> None:
    for key, value in VALID.items():
        if key != missing:
            env.setenv(key, value)
    with pytest.raises(ValidationError):
        load_env()


@pytest.mark.parametrize(
    ("key", "bad"),
    [
        ("COMPANION_PORT", "0"),
        ("LOG_LEVEL", "LOUD"),
        ("HOST_LAN_IP", "batman.local"),
        ("ADDON_TOKEN", "too-short"),
    ],
)
def test_fails_on_invalid_value(env: pytest.MonkeyPatch, key: str, bad: str) -> None:
    _set_all(env, **{key: bad})
    with pytest.raises(ValidationError):
        load_env()


def test_rejects_an_unknown_tv_os(env: pytest.MonkeyPatch) -> None:
    _set_all(env, TV_OS="roku")
    with pytest.raises(ValidationError):
        load_env()
