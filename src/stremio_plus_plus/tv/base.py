"""What every TV adapter offers: pair once, then send keys and type text."""

from collections.abc import Awaitable, Callable
from typing import Protocol

# Asks the person at the TV for the code it shows (Android TV pairing); returns it.
CodePrompt = Callable[[], Awaitable[str]]


class TvControlError(Exception):
    """The TV could not be controlled (unreachable, unknown key, unsupported text…)."""


class TvRefusedError(TvControlError):
    """The TV denied the pairing, or nobody confirmed it in time."""


class TvRemote(Protocol):
    @property
    def paired(self) -> bool:
        """True if this host holds credentials for the TV (no network check)."""
        ...

    async def pair(self, ask_code: CodePrompt) -> None:
        """Pair with the TV; someone at the TV confirms (or reads out a code)."""
        ...

    async def keys(self, *keys: str) -> None:
        """Send remote keys: common names (keys.COMMON_KEYS) or the OS's native names."""
        ...

    async def text(self, text: str) -> None:
        """Type into the focused on-screen keyboard."""
        ...
