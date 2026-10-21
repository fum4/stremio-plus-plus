import json
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from stremio_plus_plus.tls import stremio_cert

DOMAIN = "192-168-1-132.519b6502d940.stremio.rocks"
NOW = datetime(2026, 10, 21, tzinfo=UTC)


def _server_file(server_dir: Path, not_after: str) -> None:
    server_dir.mkdir(exist_ok=True)
    payload = {"domain": DOMAIN, "cert": "CERT", "key": "KEY", "notAfter": not_after}
    (server_dir / stremio_cert.CERT_FILE).write_text(json.dumps(payload))


def test_read_writes_private_pem_files(tmp_path: Path) -> None:
    _server_file(tmp_path / "srv", "2026-12-24T12:32:50Z")
    cert = stremio_cert.read(tmp_path / "srv", tmp_path / "out")
    assert cert is not None and cert.domain == DOMAIN
    assert cert.key_path.read_text() == "KEY"
    assert stat.S_IMODE(cert.key_path.stat().st_mode) == 0o600
    assert stremio_cert.read(tmp_path / "missing", tmp_path / "out") is None


@pytest.mark.asyncio
async def test_ensure_renews_only_when_close_to_expiry(tmp_path: Path) -> None:
    srv = tmp_path / "srv"
    _server_file(srv, "2026-12-24T12:32:50Z")
    calls: list[str] = []

    async def renew() -> None:
        calls.append("renew")
        _server_file(srv, "2027-03-24T12:32:50Z")

    fresh = await stremio_cert.ensure(srv, tmp_path / "out", renew, now=lambda: NOW)
    assert fresh is not None and calls == []
    late = datetime(2026, 12, 20, tzinfo=UTC)
    renewed = await stremio_cert.ensure(srv, tmp_path / "out", renew, now=lambda: late)
    assert calls == ["renew"] and renewed is not None and renewed.not_after.year == 2027


@pytest.mark.asyncio
async def test_a_failed_renewal_keeps_a_still_valid_certificate(tmp_path: Path) -> None:
    srv = tmp_path / "srv"
    _server_file(srv, "2026-10-30T00:00:00Z")

    async def renew() -> None:
        raise OSError("server down")

    kept = await stremio_cert.ensure(srv, tmp_path / "out", renew, now=lambda: NOW)
    assert kept is not None
    expired = datetime(2026, 11, 1, tzinfo=UTC)
    assert await stremio_cert.ensure(srv, tmp_path / "out", renew, now=lambda: expired) is None
