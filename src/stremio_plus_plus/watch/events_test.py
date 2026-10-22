import pytest

from stremio_plus_plus.watch.events import (
    EngineCreated,
    EngineDestroyed,
    FileRequested,
    SubtitleFetched,
    parse_line,
)

IH = "6778f903610f20668ecdacea68162e974f0201a8"


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (f"-> GET /{IH}/2 bytes=487198271-", FileRequested(IH, 2, 487198271)),
        (f"-> GET /{IH}/2 bytes=100-199 ", FileRequested(IH, 2, 100)),
        (f"-> GET /{IH}/1 ", FileRequested(IH, 1, 0)),
        (f"-> GET /{IH}/2? bytes=0-", FileRequested(IH, 2, 0)),
        (f"Engine created for {IH}", EngineCreated(IH)),
        (f"Engine {IH} destroyed", EngineDestroyed(IH)),
    ],
)
def test_parses_playback_lines(line: str, expected: object) -> None:
    assert parse_line(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        f"-> GET /{IH}/2?src=companion bytes=0-99",  # our own reads
        f"-> GET /{IH}/2/stats.json ",
        "-> GET /stats.json ",
        f"-> GET /opensubHash?videoUrl=https%3A%2F%2Fx%2F{IH}%2F2%3F",
        f"Engine {IH} is inactive, destroying it",
        "SSDP error: {",
        "",
    ],
)
def test_ignores_everything_else(line: str) -> None:
    assert parse_line(line) is None


def test_subtitle_tracks_loaded_through_the_server_are_seen() -> None:
    line = "-> GET /subtitles.vtt?from=https%3A%2F%2Fsubs5.strem.io%2Fen%2Ffile%2F19 "
    assert parse_line(line) == SubtitleFetched("https://subs5.strem.io/en/file/19")
