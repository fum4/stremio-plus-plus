import pytest

from stremio_plus_plus.tv.base import TvControlError
from stremio_plus_plus.tv.keys import ANDROID, COMMON_KEYS, SAMSUNG, WEBOS, native_keys


def test_common_names_are_translated_and_native_names_pass_through() -> None:
    assert native_keys(("HOME", "KEY_HOME", "DOWN"), SAMSUNG, "samsung") == [
        "KEY_HOME",
        "KEY_HOME",
        "KEY_DOWN",
    ]
    assert native_keys(("BACK", "FAST_FORWARD", "NETFLIX"), WEBOS, "webos") == [
        "BACK",
        "FASTFORWARD",
        "NETFLIX",
    ]
    assert native_keys(("ENTER", "KEYCODE_CAPTIONS"), ANDROID, "androidtv") == [
        "KEYCODE_DPAD_CENTER",
        "KEYCODE_CAPTIONS",
    ]


def test_a_common_name_the_os_lacks_is_an_error_not_a_pass_through() -> None:
    with pytest.raises(TvControlError, match="PLAY_PAUSE"):
        native_keys(("PLAY_PAUSE",), SAMSUNG, "samsung")


@pytest.mark.parametrize("mapping", [SAMSUNG, WEBOS, ANDROID])
def test_maps_only_cover_the_common_vocabulary(mapping: dict[str, str]) -> None:
    assert set(mapping) <= set(COMMON_KEYS)


def test_android_covers_the_whole_vocabulary() -> None:
    assert set(ANDROID) == set(COMMON_KEYS)
