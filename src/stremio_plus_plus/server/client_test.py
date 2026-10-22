import httpx
import pytest

from stremio_plus_plus.server.client import StremioServer

STATS = {
    "aa" * 20: {
        "name": "Show S01",
        "files": [
            {"name": "Show.S01E01.mkv", "length": 100},
            {"name": "Show.S01E02.mkv", "length": 200},
        ],
        "downloaded": 150,
        "downloadSpeed": 2.5,
        "peers": 7,
    }
}


def _server(handler: httpx.MockTransport) -> StremioServer:
    return StremioServer("http://srv:11470/", httpx.AsyncClient(transport=handler))


@pytest.mark.asyncio
async def test_engines_parses_stats() -> None:
    server = _server(httpx.MockTransport(lambda req: httpx.Response(200, json=STATS)))
    engines = await server.engines()
    engine = engines["aa" * 20]
    assert engine.name == "Show S01"
    assert [f.name for f in engine.files] == ["Show.S01E01.mkv", "Show.S01E02.mkv"]
    second = engine.file(1)
    assert second is not None and second.length == 200
    assert engine.file(5) is None


@pytest.mark.asyncio
async def test_remove_hits_the_remove_route() -> None:
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.url.path)
        return httpx.Response(200, json={})

    await _server(httpx.MockTransport(handler)).remove("bb" * 20)
    assert seen == [f"/{'bb' * 20}/remove"]


def test_file_url_is_tagged() -> None:
    server = _server(httpx.MockTransport(lambda req: httpx.Response(200)))
    assert server.file_url("cc" * 20, 3) == f"http://srv:11470/{'cc' * 20}/3?src=companion"


@pytest.mark.asyncio
async def test_file_progress_and_cache_dir() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/1/stats.json"):
            return httpx.Response(200, json={"streamProgress": 0.25})
        if req.url.path.endswith("/9/stats.json"):
            return httpx.Response(200, content=b"")
        return httpx.Response(200, json={"values": {"cacheRoot": "/data/srv"}})

    server = _server(httpx.MockTransport(handler))
    assert await server.file_progress("aa" * 20, 1) == 0.25
    assert await server.file_progress("aa" * 20, 9) is None
    assert str(await server.cache_dir()) == "/data/srv/stremio-cache"


@pytest.mark.asyncio
async def test_opensub_hash_asks_the_server_about_our_tagged_url() -> None:
    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(str(req.url.params["videoUrl"]))
        return httpx.Response(
            200, json={"error": None, "result": {"size": 9, "hash": "cfff08ce8455342c"}}
        )

    server = _server(httpx.MockTransport(handler))
    assert await server.opensub_hash(server.file_url("aa" * 20, 1)) == "cfff08ce8455342c"
    assert seen == [f"http://srv:11470/{'aa' * 20}/1?src=companion"]
