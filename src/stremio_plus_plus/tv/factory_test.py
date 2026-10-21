from ipaddress import IPv4Address
from pathlib import Path

import pytest

from stremio_plus_plus.config.env import Env
from stremio_plus_plus.tv.androidtv import AndroidTvRemote
from stremio_plus_plus.tv.factory import PAIR_HINT, make_remote
from stremio_plus_plus.tv.firetv import FireTvRemote
from stremio_plus_plus.tv.samsung import SamsungRemote
from stremio_plus_plus.tv.webos import WebOsRemote


@pytest.mark.parametrize(
    ("tv_os", "cls"),
    [
        ("samsung", SamsungRemote),
        ("webos", WebOsRemote),
        ("androidtv", AndroidTvRemote),
        ("firetv", FireTvRemote),
    ],
)
def test_picks_the_adapter_for_tv_os(tmp_path: Path, tv_os: str, cls: type) -> None:
    env = Env.model_construct(
        tv_host=IPv4Address("10.0.0.9"), tv_os=tv_os, companion_data_dir=tmp_path
    )
    assert isinstance(make_remote(env), cls)
    assert tv_os in PAIR_HINT


def test_samsung_keeps_the_existing_token_file(tmp_path: Path) -> None:
    (tmp_path / "tv-token").write_text("123")
    env = Env.model_construct(
        tv_host=IPv4Address("10.0.0.9"), tv_os="samsung", companion_data_dir=tmp_path
    )
    assert make_remote(env).paired
