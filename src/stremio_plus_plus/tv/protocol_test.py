import base64
import json

from stremio_plus_plus.tv.protocol import (
    Connected,
    Other,
    Refused,
    channel_url,
    key_message,
    parse_event,
    text_messages,
)


def test_channel_url_encodes_the_client_name_and_adds_the_token() -> None:
    url = channel_url("192.168.1.134", 8002, "stremio++", None)
    assert url.startswith("wss://192.168.1.134:8002/api/v2/channels/samsung.remote.control?name=")
    assert "token" not in url
    assert channel_url("tv", 8002, "x", "12345678").endswith("&token=12345678")


def test_parse_event_handles_connect_refusal_and_touch_noise() -> None:
    assert parse_event('{"event": "ms.channel.connect", "data": {"token": "42"}}') == Connected(
        "42"
    )
    assert parse_event('{"event": "ms.channel.connect", "data": {}}') == Connected(None)
    assert parse_event('{"event": "ms.channel.unauthorized"}') == Refused()
    assert parse_event('{"event": "ms.remote.touchDisable"}') == Other("ms.remote.touchDisable")


def test_messages() -> None:
    assert json.loads(key_message("KEY_HOME"))["params"]["DataOfCmd"] == "KEY_HOME"
    typed, done = (json.loads(m) for m in text_messages("https://ă"))
    assert base64.b64decode(typed["params"]["Cmd"]).decode() == "https://ă"
    assert done["params"]["TypeOfRemote"] == "SendInputEnd"
