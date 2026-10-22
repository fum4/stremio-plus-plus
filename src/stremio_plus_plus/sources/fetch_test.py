from typing import Any

from stremio_plus_plus.sources.constants import DEFAULT_ADDONS
from stremio_plus_plus.sources.fetch import stream_addons


def _addon(id_: str, url: str, resources: list[Any], types: list[str]) -> dict[str, Any]:
    manifest = {"id": id_, "resources": resources, "types": types}
    return {"transportUrl": url, "manifest": manifest}


def test_stream_addons_in_collection_order_without_ours_or_plain_http() -> None:
    addons = [
        _addon(
            "io.github.fum4.stremio-plus-plus", "https://me/t/manifest.json", ["stream"], ["movie"]
        ),
        _addon(
            "com.stremio.torrentio",
            "https://torrentio.strem.fun/manifest.json",
            ["stream"],
            ["movie", "series"],
        ),
        _addon("org.thepiratebay", "http://tpb.lan/manifest.json", ["stream"], ["movie"]),
        _addon("org.cinemeta", "https://cinemeta/manifest.json", ["meta"], ["movie"]),
        _addon(
            "org.tpbplus",
            "https://tpb.plus/manifest.json",
            [{"name": "stream", "types": ["movie"]}],
            [],
        ),
    ]
    assert stream_addons(addons, "movie", "tt1") == [
        "https://torrentio.strem.fun",
        "https://tpb.plus",
    ]
    assert stream_addons(addons, "series", "tt1:1:1") == ["https://torrentio.strem.fun"]


def test_no_account_or_no_stream_addons_falls_back_to_the_defaults() -> None:
    assert stream_addons(None, "movie", "tt1") == list(DEFAULT_ADDONS)
    assert stream_addons([], "movie", "tt1") == list(DEFAULT_ADDONS)
