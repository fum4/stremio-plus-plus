import asyncio

import pytest

from stremio_plus_plus.downloads.fake_server_test_support import FakeServer
from stremio_plus_plus.downloads.pins import Pinner

IH = "aa" * 20


@pytest.mark.asyncio
async def test_pin_opens_one_tagged_stream_and_release_closes_it() -> None:
    fake = FakeServer({}, {})
    pinner = Pinner(fake.http, fake.client)
    assert pinner.pin(IH, 1) is True
    assert pinner.pin(IH, 1) is False  # already pinned
    await asyncio.sleep(0.05)
    assert fake.streams == [f"/{IH}/1"] and pinner.pinned() == {(IH, 1)}
    await pinner.release(IH, 1)
    assert pinner.pinned() == set()


@pytest.mark.asyncio
async def test_release_engine_drops_all_its_pins() -> None:
    fake = FakeServer({}, {})
    pinner = Pinner(fake.http, fake.client)
    pinner.pin(IH, 0)
    pinner.pin(IH, 1)
    pinner.pin("bb" * 20, 0)
    await pinner.release_engine(IH)
    assert pinner.pinned() == {("bb" * 20, 0)}
    await pinner.close()
