"""Samsung Tizen TV remote protocol (wss://<tv>:8002/api/v2/channels/samsung.remote.control).

Verified on the owner's UE43TU7092 (Tizen 5.5): the TV sends `ms.remote.touchDisable` /
`ms.remote.touchEnable` before `ms.channel.connect`, which carries the pairing token on first
pairing. `samsungtvws` 3.0.6 treats those first events as failures, hence this small client.
"""

import base64
import json
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import quote


def channel_url(host: str, port: int, client_name: str, token: str | None) -> str:
    name = quote(base64.b64encode(client_name.encode()).decode())
    url = f"wss://{host}:{port}/api/v2/channels/samsung.remote.control?name={name}"
    return f"{url}&token={token}" if token else url


@dataclass(frozen=True)
class Connected:
    token: str | None


@dataclass(frozen=True)
class Refused:
    pass


@dataclass(frozen=True)
class Other:
    name: str


def parse_event(raw: str) -> Connected | Refused | Other:
    event = cast(dict[str, Any], json.loads(raw))
    name = str(event.get("event", ""))
    if name == "ms.channel.connect":
        data = cast(dict[str, Any], event.get("data") or {})
        token = data.get("token")
        return Connected(str(token) if token else None)
    if name in ("ms.channel.unauthorized", "ms.channel.timeOut"):
        return Refused()
    return Other(name)


def key_message(key: str) -> str:
    return json.dumps(
        {
            "method": "ms.remote.control",
            "params": {
                "Cmd": "Click",
                "DataOfCmd": key,
                "Option": "false",
                "TypeOfRemote": "SendRemoteKey",
            },
        }
    )


def text_messages(text: str) -> list[str]:
    """Type into the focused on-screen keyboard, then close it."""
    typed = json.dumps(
        {
            "method": "ms.remote.control",
            "params": {
                "Cmd": base64.b64encode(text.encode()).decode(),
                "DataOfCmd": "base64",
                "TypeOfRemote": "SendInputString",
            },
        }
    )
    done = json.dumps({"method": "ms.remote.control", "params": {"TypeOfRemote": "SendInputEnd"}})
    return [typed, done]
