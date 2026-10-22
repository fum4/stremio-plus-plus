from pathlib import Path

import pytest
from pydantic import ValidationError

from stremio_plus_plus.config.env import load_env

REQUIRED = {
    "STREMIO_SERVER_URL": "http://127.0.0.1:11470",
    "STREMIO_SERVER_LOG": "~/Library/Logs/stremio-plus-plus/server.log",
    "STREMIO_SERVER_DATA_DIR": "~/Library/Application Support/stremio-plus-plus/stremio-server",
    "STREMIO_SERVER_SETTINGS": "infra/stremio-server/settings.json",
    "COMPANION_HOST": "0.0.0.0",
    "COMPANION_PORT": "11471",
    "COMPANION_DATA_DIR": "/tmp/companion-data",
    "CONFIG_DIR": "~/.config/stremio-plus-plus",
    "UI_DIR": "web/dist",
    "CLAUDE_CLI": "~/.local/bin/claude",
    "ADDON_HTTPS_PORT": "8443",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "json",
}
# The owner's personal setup; a fresh install has none of these.
OPTIONAL = {
    "HOST_LAN_IP": "192.168.1.132",
    "TV_HOST": "192.168.1.134",
    "TV_OS": "samsung",
    "ADDON_DOMAIN": "stremio.nomadware.io",
    "ADDON_TOKEN": "x" * 32,
}
VALID = REQUIRED | OPTIONAL


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


def test_a_fresh_install_needs_none_of_the_personal_values(env: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED.items():
        env.setenv(key, value)
    loaded = load_env()
    assert (loaded.host_lan_ip, loaded.addon_domain, loaded.addon_token, loaded.tv_os) == (
        None,
        None,
        None,
        None,
    )


def test_an_empty_optional_value_means_unset(env: pytest.MonkeyPatch) -> None:
    _set_all(env, ADDON_DOMAIN="", TV_HOST="", TV_OS="", ADDON_TOKEN="")
    loaded = load_env()
    assert (loaded.addon_domain, loaded.tv_host, loaded.tv_os, loaded.addon_token) == (
        None,
        None,
        None,
        None,
    )


@pytest.mark.parametrize("missing", sorted(REQUIRED))
def test_fails_on_any_missing_required_value(env: pytest.MonkeyPatch, missing: str) -> None:
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
