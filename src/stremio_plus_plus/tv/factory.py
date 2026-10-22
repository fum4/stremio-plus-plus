"""Pick the adapter for the TV's OS. Only Samsung is verified on a real TV (see each module)."""

from ipaddress import IPv4Address
from pathlib import Path

from stremio_plus_plus.config.settings import TvOs
from stremio_plus_plus.tv.androidtv import AndroidTvRemote
from stremio_plus_plus.tv.base import TvControlError, TvRemote
from stremio_plus_plus.tv.constants import (
    ANDROIDTV_CERT_FILE,
    ANDROIDTV_KEY_FILE,
    FIRETV_KEY_FILE,
    TOKEN_FILE,
    WEBOS_KEY_FILE,
)
from stremio_plus_plus.tv.firetv import FireTvRemote
from stremio_plus_plus.tv.samsung import SamsungRemote
from stremio_plus_plus.tv.webos import WebOsRemote


def make_remote(target: tuple[IPv4Address, TvOs] | None, data: Path) -> TvRemote:
    """`target` from config.host.tv_target; credentials live in the companion's data dir."""
    if target is None:
        raise TvControlError(
            "no TV configured: run the setup's TV step, or set [tv] in config.toml"
        )
    host, os_ = str(target[0]), target[1]
    match os_:
        case "samsung":
            return SamsungRemote(host, data / TOKEN_FILE)
        case "webos":
            return WebOsRemote(host, data / WEBOS_KEY_FILE)
        case "androidtv":
            return AndroidTvRemote(host, data / ANDROIDTV_CERT_FILE, data / ANDROIDTV_KEY_FILE)
        case "firetv":
            return FireTvRemote(host, data / FIRETV_KEY_FILE)


# What the person at the TV does to pair, per OS (CLI and doctor wording).
PAIR_HINT = {
    "samsung": "press Allow on the TV",
    "webos": "accept the prompt on the TV",
    "androidtv": "type the code the TV shows",
    "firetv": "turn on ADB debugging on the TV first, then tick Always allow and press OK",
}
