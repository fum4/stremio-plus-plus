import stat
from pathlib import Path

import pytest
from androidtvremote2 import InvalidAuth

from stremio_plus_plus.tv.androidtv import AndroidTvClientLike, AndroidTvRemote, normalize_code
from stremio_plus_plus.tv.base import TvControlError, TvRefusedError


class FakeClient:
    def __init__(self, name: str, certfile: str, keyfile: str, host: str) -> None:
        self.args = (name, certfile, keyfile, host)
        self.calls: list[tuple[str, object]] = []
        self.good_code = "A1B2C3"

    async def async_generate_cert_if_missing(self) -> bool:
        cert, key = Path(self.args[1]), Path(self.args[2])
        if cert.is_file() and key.is_file():  # like the library: reuse an existing pair
            return False
        cert.write_text("CERT")
        key.write_text("KEY")
        return True

    async def async_start_pairing(self) -> None:
        self.calls.append(("start", None))

    async def async_finish_pairing(self, pairing_code: str) -> None:
        if pairing_code != self.good_code:
            raise InvalidAuth("bad code")
        self.calls.append(("finish", pairing_code))

    async def async_connect(self) -> None:
        self.calls.append(("connect", None))

    def send_key_command(self, key_code: int | str, direction: int | str = "SHORT") -> None:
        if key_code == "KEYCODE_NOPE":
            raise ValueError(key_code)
        self.calls.append(("key", key_code))

    def send_text(self, text: str) -> None:
        self.calls.append(("text", text))

    def disconnect(self) -> None:
        self.calls.append(("disconnect", None))


@pytest.fixture
def setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[AndroidTvRemote, list[FakeClient]]:
    monkeypatch.setattr("stremio_plus_plus.tv.androidtv.KEY_DELAY_S", 0)
    clients: list[FakeClient] = []

    def factory(name: str, cert: str, key: str, host: str) -> AndroidTvClientLike:
        clients.append(FakeClient(name, cert, key, host))
        return clients[-1]

    remote = AndroidTvRemote("10.0.0.6", tmp_path / "c.pem", tmp_path / "k.pem", factory)
    return remote, clients


def _code(value: str):
    async def ask() -> str:
        return value

    return ask


def test_normalize_code() -> None:
    assert normalize_code(" a1b 2c3\n") == "A1B2C3"


@pytest.mark.asyncio
async def test_pair_with_the_code_shown_on_the_tv(
    setup: tuple[AndroidTvRemote, list[FakeClient]], tmp_path: Path
) -> None:
    remote, clients = setup
    await remote.pair(_code("a1b2c3"))
    assert remote.paired
    assert clients[0].args[0] == "stremio++"
    assert clients[0].calls == [("start", None), ("finish", "A1B2C3"), ("disconnect", None)]
    for name in ("c.pem", "k.pem"):
        assert stat.S_IMODE((tmp_path / name).stat().st_mode) == 0o600


@pytest.mark.asyncio
async def test_a_wrong_code_leaves_no_credentials(
    setup: tuple[AndroidTvRemote, list[FakeClient]],
) -> None:
    remote, _ = setup
    with pytest.raises(TvRefusedError):
        await remote.pair(_code("000000"))
    assert not remote.paired


@pytest.mark.asyncio
async def test_keys_and_text(setup: tuple[AndroidTvRemote, list[FakeClient]]) -> None:
    remote, clients = setup
    with pytest.raises(TvRefusedError, match="not paired"):
        await remote.keys("HOME")
    await remote.pair(_code("A1B2C3"))
    await remote.keys("HOME", "PLAY_PAUSE", "KEYCODE_CAPTIONS")
    assert clients[-1].calls == [
        ("connect", None),
        ("key", "KEYCODE_HOME"),
        ("key", "KEYCODE_MEDIA_PLAY_PAUSE"),
        ("key", "KEYCODE_CAPTIONS"),
        ("disconnect", None),
    ]
    await remote.text("http://x")
    assert ("text", "http://x") in clients[-1].calls
    with pytest.raises(TvControlError, match="unknown"):
        await remote.keys("KEYCODE_NOPE")


@pytest.mark.asyncio
async def test_a_failed_re_pair_keeps_the_pairing_the_tv_already_accepted(
    setup: tuple[AndroidTvRemote, list[FakeClient]], tmp_path: Path
) -> None:
    remote, _ = setup
    await remote.pair(_code("a1b2c3"))
    with pytest.raises(TvRefusedError):
        await remote.pair(_code("ZZZZZZ"))  # mistyped code on a re-pair
    assert remote.paired
