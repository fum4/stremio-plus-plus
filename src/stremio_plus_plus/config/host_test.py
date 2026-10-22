from ipaddress import IPv4Address
from pathlib import Path

import pytest

from stremio_plus_plus.config import host
from stremio_plus_plus.config.env import Env
from stremio_plus_plus.config.settings_file import SettingsFile


def _env(tmp_path: Path, **values: object) -> Env:
    base: dict[str, object] = {
        "stremio_server_url": "http://127.0.0.1:11470",
        "stremio_server_log": tmp_path / "server.log",
        "companion_log": tmp_path / "companion.log",
        "stremio_server_data_dir": tmp_path / "server",
        "stremio_server_settings": tmp_path / "settings.json",
        "companion_host": "0.0.0.0",
        "companion_port": 11471,
        "companion_data_dir": tmp_path,
        "config_dir": tmp_path / "config",
        "ui_dir": tmp_path / "ui",
        "claude_cli": tmp_path / "claude",
        "addon_https_port": 8443,
        "log_level": "INFO",
        "log_format": "json",
        # Explicit None: the developer's own environment (mise, .env.local) must not leak in.
        "host_lan_ip": None,
        "addon_token": None,
        "addon_domain": None,
    }
    return Env.model_validate(base | values)


def test_env_ip_wins_else_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(host, "detect_lan_ip", lambda: IPv4Address("10.0.0.7"))
    assert host.lan_ip(_env(tmp_path)) == IPv4Address("10.0.0.7")
    pinned = _env(tmp_path, host_lan_ip="192.168.1.132")
    assert host.lan_ip(pinned) == IPv4Address("192.168.1.132")
    monkeypatch.setattr(host, "detect_lan_ip", lambda: None)
    with pytest.raises(host.HostError):
        host.lan_ip(_env(tmp_path))


def test_token_is_generated_once_and_kept(tmp_path: Path) -> None:
    env, settings_file = _env(tmp_path), SettingsFile(tmp_path / "config")
    first = host.addon_token(env, settings_file)
    assert len(first) >= 24
    assert host.addon_token(env, SettingsFile(tmp_path / "config")) == first
    assert host.addon_token(_env(tmp_path, addon_token="t" * 32), settings_file) == "t" * 32
