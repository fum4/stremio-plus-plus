"""Pick the adapter for TV_OS. Only Samsung is verified on a real TV (see each module)."""

from stremio_plus_plus.config.env import Env
from stremio_plus_plus.tv.androidtv import AndroidTvRemote
from stremio_plus_plus.tv.base import TvRemote
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


def make_remote(env: Env) -> TvRemote:
    host, data = str(env.tv_host), env.companion_data_dir
    match env.tv_os:
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
