from collections.abc import AsyncIterator

import pytest

from stremio_companion.watch.events import EngineCreated, Event, FileRequested
from stremio_companion.watch.tracker import run_tracker

IH = "aa" * 20


async def _lines(*items: str) -> AsyncIterator[str]:
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_dispatches_parsed_events_and_survives_a_failing_handler() -> None:
    seen: list[Event] = []

    async def broken(event: Event) -> None:
        raise RuntimeError("boom")

    async def recorder(event: Event) -> None:
        seen.append(event)

    await run_tracker(
        _lines(f"Engine created for {IH}", "noise", f"-> GET /{IH}/0 bytes=5-"), [broken, recorder]
    )
    assert seen == [EngineCreated(IH), FileRequested(IH, 0, 5)]
