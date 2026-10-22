import httpx
import pytest

from stremio_plus_plus.meta.cinemeta import Cinemeta, parse_meta

META = {
    "name": "MobLand",
    "year": "2025-",
    "poster": "https://images.metahub.space/poster/small/tt31510819/img",
    "videos": [{"season": 1, "number": 3, "episode": 3, "name": "Plan B", "thumbnail": "t.jpg"}],
}


def test_episode_titles() -> None:
    title = parse_meta(META, 1, 3)
    assert (title.name, title.subtitle, title.still) == ("MobLand", "S01E03 · Plan B", "t.jpg")
    assert parse_meta(META, None, None).subtitle is None


@pytest.mark.asyncio
async def test_looks_up_once_and_skips_non_imdb_ids() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"meta": META})

    meta = Cinemeta(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    first = await meta.title("series", "tt31510819:1:3")
    again = await meta.title("series", "tt31510819:1:3")
    assert first == again and first is not None and first.name == "MobLand"
    assert calls == ["/meta/series/tt31510819.json"]
    assert await meta.title("series", "kitsu:123:4") is None
