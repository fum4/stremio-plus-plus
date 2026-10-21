"""Key sequences that drive the Stremio app on a TV, per TV OS and per action.

Each one is recorded on a real TV and verified there (docs/runbooks/tv-setup.md § Automation);
an OS without one falls back to "focus the field, then let the host type". A sequence ends with
the field focused and the URL typed: success is confirmed by the TV showing up in the server log
(watch/clients.py), never assumed.
"""

import asyncio
from dataclasses import dataclass
from typing import Literal

from stremio_plus_plus.config.settings import TvOs
from stremio_plus_plus.tv.base import TvRemote

Action = Literal["server", "revert"]


@dataclass(frozen=True)
class Keys:
    keys: tuple[str, ...]


@dataclass(frozen=True)
class Type:
    """Types the action's URL into the focused field."""


@dataclass(frozen=True)
class Wait:
    seconds: float


Step = Keys | Type | Wait

# Settings → Streaming → Server URL, then the URL. Empty until recorded on that OS's TV.
SET_SERVER_URL: dict[TvOs, tuple[Step, ...]] = {}


def available(os_: TvOs) -> bool:
    return os_ in SET_SERVER_URL


async def run(remote: TvRemote, steps: tuple[Step, ...], url: str) -> None:
    for step in steps:
        match step:
            case Keys(keys):
                await remote.keys(*keys)
            case Type():
                await remote.text(url)
            case Wait(seconds):
                await asyncio.sleep(seconds)
