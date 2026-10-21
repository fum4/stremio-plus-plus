"""One key vocabulary for every TV OS, mapped to each OS's native key names.

A name in COMMON_KEYS is translated; any other name is passed through untouched as a native key
(KEY_HOME on Samsung, HOME on webOS, KEYCODE_HOME on Android TV / Fire TV). A common name an OS
has no single key for (e.g. PLAY_PAUSE on Samsung/webOS, which only have PLAY and PAUSE) is an
error rather than a guess.
"""

from collections.abc import Mapping

from stremio_plus_plus.tv.base import TvControlError

COMMON_KEYS = (
    "HOME",
    "BACK",
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "ENTER",
    "PLAY",
    "PAUSE",
    "PLAY_PAUSE",
    "STOP",
    "REWIND",
    "FAST_FORWARD",
    "VOLUME_UP",
    "VOLUME_DOWN",
    "MUTE",
    "MENU",
    "INFO",
)

SAMSUNG: Mapping[str, str] = {
    "HOME": "KEY_HOME",
    "BACK": "KEY_RETURN",
    "UP": "KEY_UP",
    "DOWN": "KEY_DOWN",
    "LEFT": "KEY_LEFT",
    "RIGHT": "KEY_RIGHT",
    "ENTER": "KEY_ENTER",
    "PLAY": "KEY_PLAY",
    "PAUSE": "KEY_PAUSE",
    "STOP": "KEY_STOP",
    "REWIND": "KEY_REWIND",
    "FAST_FORWARD": "KEY_FF",
    "VOLUME_UP": "KEY_VOLUP",
    "VOLUME_DOWN": "KEY_VOLDOWN",
    "MUTE": "KEY_MUTE",
    "MENU": "KEY_MENU",
    "INFO": "KEY_INFO",
}

# Button names of webOS's pointer input socket (aiowebostv.buttons.BUTTONS).
WEBOS: Mapping[str, str] = {
    "HOME": "HOME",
    "BACK": "BACK",
    "UP": "UP",
    "DOWN": "DOWN",
    "LEFT": "LEFT",
    "RIGHT": "RIGHT",
    "ENTER": "ENTER",
    "PLAY": "PLAY",
    "PAUSE": "PAUSE",
    "STOP": "STOP",
    "REWIND": "REWIND",
    "FAST_FORWARD": "FASTFORWARD",
    "VOLUME_UP": "VOLUMEUP",
    "VOLUME_DOWN": "VOLUMEDOWN",
    "MUTE": "MUTE",
    "MENU": "MENU",
    "INFO": "INFO",
}

# Android KeyEvent names: the ATV remote v2 protobuf enum and `input keyevent` share them.
ANDROID: Mapping[str, str] = {
    "HOME": "KEYCODE_HOME",
    "BACK": "KEYCODE_BACK",
    "UP": "KEYCODE_DPAD_UP",
    "DOWN": "KEYCODE_DPAD_DOWN",
    "LEFT": "KEYCODE_DPAD_LEFT",
    "RIGHT": "KEYCODE_DPAD_RIGHT",
    "ENTER": "KEYCODE_DPAD_CENTER",
    "PLAY": "KEYCODE_MEDIA_PLAY",
    "PAUSE": "KEYCODE_MEDIA_PAUSE",
    "PLAY_PAUSE": "KEYCODE_MEDIA_PLAY_PAUSE",
    "STOP": "KEYCODE_MEDIA_STOP",
    "REWIND": "KEYCODE_MEDIA_REWIND",
    "FAST_FORWARD": "KEYCODE_MEDIA_FAST_FORWARD",
    "VOLUME_UP": "KEYCODE_VOLUME_UP",
    "VOLUME_DOWN": "KEYCODE_VOLUME_DOWN",
    "MUTE": "KEYCODE_VOLUME_MUTE",
    "MENU": "KEYCODE_MENU",
    "INFO": "KEYCODE_INFO",
}


def native_keys(keys: tuple[str, ...], mapping: Mapping[str, str], os_name: str) -> list[str]:
    """Translate common names; pass native ones through unchanged."""
    out: list[str] = []
    for key in keys:
        if key in mapping:
            out.append(mapping[key])
        elif key in COMMON_KEYS:
            raise TvControlError(f"{os_name} has no single key for {key}")
        else:
            out.append(key)
    return out
