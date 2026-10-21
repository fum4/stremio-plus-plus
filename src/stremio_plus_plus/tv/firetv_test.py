import shlex
import stat
from pathlib import Path

import pytest
from adb_shell.exceptions import DeviceAuthError  # pyright: ignore[reportMissingTypeStubs]

from stremio_plus_plus.tv.base import TvControlError, TvRefusedError
from stremio_plus_plus.tv.firetv import (
    AdbDeviceLike,
    FireTvRemote,
    keyevent_command,
    text_command,
)


def test_keyevent_command_accepts_only_key_names() -> None:
    assert keyevent_command("KEYCODE_HOME") == "input keyevent KEYCODE_HOME"
    assert keyevent_command("3") == "input keyevent 3"
    for bad in ("KEYCODE_HOME; reboot", "home", "$(id)", "1234"):
        with pytest.raises(TvControlError):
            keyevent_command(bad)


def test_text_command_quotes_and_encodes_spaces() -> None:
    command = text_command("it's a test")
    assert shlex.split(command) == ["input", "text", "it's%sa%stest"]
    assert text_command("http://192.168.1.2:11470") == "input text http://192.168.1.2:11470"
    with pytest.raises(TvControlError):
        text_command("ăîș")


class FakeDevice:
    def __init__(self, *, allow: bool = True) -> None:
        self.allow = allow
        self.shells: list[str] = []
        self.auth_timeout: float | None = None
        self.closed = False

    async def connect(self, rsa_keys: list[object], auth_timeout_s: float) -> bool:
        assert len(rsa_keys) == 1
        self.auth_timeout = auth_timeout_s
        if not self.allow:
            raise DeviceAuthError("denied")
        return True

    async def shell(self, command: str) -> str:
        self.shells.append(command)
        return ""

    async def close(self) -> None:
        self.closed = True


def _remote(tmp_path: Path, devices: list[FakeDevice], allow: bool = True) -> FireTvRemote:
    def factory(host: str, port: int) -> AdbDeviceLike:
        assert (host, port) == ("10.0.0.7", 5555)
        devices.append(FakeDevice(allow=allow))
        return devices[-1]

    return FireTvRemote("10.0.0.7", tmp_path / "tv-firetv-adbkey", factory)


async def _no_code() -> str:
    raise AssertionError("Fire TV never asks for a code")


@pytest.mark.asyncio
async def test_pair_makes_a_private_key_and_keys_become_shell_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("stremio_plus_plus.tv.firetv.KEY_DELAY_S", 0)
    devices: list[FakeDevice] = []
    remote = _remote(tmp_path, devices)
    await remote.pair(_no_code)
    key = tmp_path / "tv-firetv-adbkey"
    assert stat.S_IMODE(key.stat().st_mode) == 0o600
    assert devices[0].auth_timeout == 60.0
    assert devices[0].closed
    await remote.keys("HOME", "ENTER")
    assert devices[1].shells == [
        "input keyevent KEYCODE_HOME",
        "input keyevent KEYCODE_DPAD_CENTER",
    ]
    await remote.text("a b")
    assert devices[2].shells == ["input text a%sb"]


@pytest.mark.asyncio
async def test_a_denied_prompt_removes_the_unused_key(tmp_path: Path) -> None:
    remote = _remote(tmp_path, [], allow=False)
    with pytest.raises(TvRefusedError):
        await remote.pair(_no_code)
    assert not remote.paired
    assert not (tmp_path / "tv-firetv-adbkey.pub").exists()
