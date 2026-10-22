"""When a Stremio app (the TV) last used the server: the setup's proof that the TV is connected.

Kept in a small file so it survives restarts: a TV that connected yesterday and sits idle today
is still connected.
"""

import time
from collections.abc import Callable
from pathlib import Path

from stremio_plus_plus.watch.events import ClientSeen, Event, FileRequested, SubtitleFetched

FILE = "client-last-seen"
WRITE_EVERY_S = 60.0  # the TV polls; don't rewrite the file on every request


class ClientMonitor:
    def __init__(self, data_dir: Path, clock: Callable[[], float] = time.time) -> None:
        self._path = data_dir / FILE
        self._clock = clock
        try:
            self.last_seen: float | None = float(self._path.read_text())
        except OSError, ValueError:
            self.last_seen = None

    async def __call__(self, event: Event) -> None:
        if not isinstance(event, ClientSeen | FileRequested | SubtitleFetched):
            return
        now = self._clock()
        if self.last_seen is None or now - self.last_seen >= WRITE_EVERY_S:
            self._path.write_text(str(now))
        self.last_seen = now

    def seen_since(self, t: float) -> bool:
        return self.last_seen is not None and self.last_seen >= t
