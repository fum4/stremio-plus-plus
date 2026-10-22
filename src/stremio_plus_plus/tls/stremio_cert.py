"""Serve the addon under the streaming server's own certificate: no domain needed.

With remoteHttps set, server.js gets a Let's Encrypt wildcard for *.<id>.stremio.rocks from
Stremio's API and stores it, key included, in `<APP_PATH>/httpsCert.json` (server.js:72124;
docs/research/stremio-internals.md § Remote HTTPS). `<ip-dashed>.<id>.stremio.rocks` resolves
publicly to the LAN IP, so the companion can serve HTTPS under that same name on its own port.
Renewal goes through the server's `GET /get-https`, which rewrites the file.

The key comes from a public API, so this TLS gives clients the secure context they demand, not
secrecy against someone on the LAN; the addon token is the access control, as with a domain.
"""

import json
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import structlog

log = structlog.get_logger()
CERT_FILE = "httpsCert.json"
RENEW_BEFORE = timedelta(days=14)


@dataclass(frozen=True)
class StremioCert:
    domain: str
    not_after: datetime
    cert_path: Path
    key_path: Path


def _write_private(path: Path, text: str) -> None:
    if path.exists() and path.read_text() == text:
        return
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    tmp.replace(path)


def server_domain(server_data_dir: Path) -> str | None:
    """The name the server itself is reachable under (the TV's server URL), without the key."""
    try:
        return str(json.loads((server_data_dir / CERT_FILE).read_text())["domain"])
    except OSError, ValueError, KeyError:
        return None


def read(server_data_dir: Path, out_dir: Path) -> StremioCert | None:
    """The server's current certificate as PEM files uvicorn can load, or None if there's none."""
    try:
        raw = cast(dict[str, Any], json.loads((server_data_dir / CERT_FILE).read_text()))
        domain, cert, key = str(raw["domain"]), str(raw["cert"]), str(raw["key"])
        not_after = datetime.fromisoformat(str(raw["notAfter"]))
    except OSError, ValueError, KeyError:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir.chmod(0o700)
    _write_private(out_dir / "cert.pem", cert)
    _write_private(out_dir / "key.pem", key)
    return StremioCert(domain, not_after, out_dir / "cert.pem", out_dir / "key.pem")


async def ensure(
    server_data_dir: Path,
    out_dir: Path,
    renew: Callable[[], Awaitable[None]],
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> StremioCert | None:
    """A certificate valid for at least RENEW_BEFORE, renewing it through the server if not."""
    current = read(server_data_dir, out_dir)
    if current is not None and current.not_after - now() > RENEW_BEFORE:
        return current
    try:
        await renew()
    except Exception as exc:  # server down or Stremio's API unreachable: keep what we have
        log.warning("stremio_cert_renew_failed", error=str(exc))
        return current if current is not None and current.not_after > now() else None
    renewed = read(server_data_dir, out_dir)
    log.info("stremio_cert_renewed", domain=renewed.domain if renewed else None)
    return renewed
