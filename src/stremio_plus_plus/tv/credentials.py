"""Per-OS pairing credentials on disk: created mode 600, never readable by other users."""

import os
from pathlib import Path


def write_secret(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(content)
    path.chmod(0o600)  # O_CREAT's mode does not apply to an existing file


def restrict(*paths: Path) -> None:
    """Tighten files a library wrote with default permissions."""
    for path in paths:
        if path.exists():
            path.chmod(0o600)


def remove(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)
