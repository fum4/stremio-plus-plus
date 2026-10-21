from pathlib import Path

import pytest

from stremio_plus_plus.watch.clients import ClientMonitor
from stremio_plus_plus.watch.events import ClientSeen, EngineCreated, parse_line


def test_untagged_requests_are_a_client_and_tagged_ones_are_us() -> None:
    assert parse_line("-> GET /settings ") == ClientSeen("/settings")
    assert parse_line("-> GET /stats.json?foo=1") == ClientSeen("/stats.json")
    assert parse_line("-> GET /settings?src=companion") is None
    assert parse_line("-> GET /get-https?src=companion&ipAddress=1.2.3.4") is None


@pytest.mark.asyncio
async def test_last_seen_survives_a_restart(tmp_path: Path) -> None:
    now = [1000.0]
    monitor = ClientMonitor(tmp_path, clock=lambda: now[0])
    assert monitor.last_seen is None
    await monitor(EngineCreated("ab" * 20))
    assert monitor.last_seen is None
    await monitor(ClientSeen("/settings"))
    assert monitor.seen_since(999) and not monitor.seen_since(1001)
    assert ClientMonitor(tmp_path).last_seen == 1000.0
