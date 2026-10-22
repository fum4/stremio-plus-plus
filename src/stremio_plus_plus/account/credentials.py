"""The Stremio authKey on disk: `<data dir>/stremio-auth.json` as {"authKey": "…"}, mode 600.

Only the key is kept, never the password. Same file and format as set up by hand on the owner's
host, so an existing login carries over.
"""

import json
import os
from pathlib import Path

FILE = "stremio-auth.json"


class AuthFile:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / FILE

    def load(self) -> str | None:
        try:
            key = json.loads(self.path.read_text()).get("authKey")
        except OSError, ValueError, AttributeError:
            return None
        return str(key) if key else None

    def save(self, auth_key: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as out:
            json.dump({"authKey": auth_key}, out)
        tmp.replace(self.path)
        self.path.chmod(0o600)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
