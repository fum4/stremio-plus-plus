from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

import pytest

from stremio_plus_plus.tv.androidtv import AndroidTvRemote
from stremio_plus_plus.tv.base import TvControlError
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
def test_picks_the_adapter_for_tv_os(tmp_path: Path, tv_os: Any, cls: type) -> None:
    assert isinstance(make_remote((IPv4Address("10.0.0.9"), tv_os), tmp_path), cls)
    assert tv_os in PAIR_HINT


def test_samsung_keeps_the_existing_token_file(tmp_path: Path) -> None:
    (tmp_path / "tv-token").write_text("123")
    assert make_remote((IPv4Address("10.0.0.9"), "samsung"), tmp_path).paired


def test_no_tv_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(TvControlError, match="no TV configured"):
        make_remote(None, tmp_path)
