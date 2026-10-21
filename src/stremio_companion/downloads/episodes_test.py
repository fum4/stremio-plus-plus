import pytest

from stremio_companion.downloads.episodes import next_episode, parse_episode
from stremio_companion.server.models import Engine, TorrentFile


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("MobLand.S01E03.Plan.B.2160p.mkv", (1, 3)),
        ("Show/Season 2/show.s02e10.1080p.mkv", (2, 10)),
        ("Show - 1x07 - Title.mp4", (1, 7)),
        ("Movie.2023.2160p.mkv", None),
        ("Show.S01.Complete/readme.txt", None),
    ],
)
def test_parse_episode(name: str, expected: tuple[int, int] | None) -> None:
    assert parse_episode(name) == expected


def _engine(*names_and_sizes: tuple[str, int]) -> Engine:
    files = tuple(TorrentFile(i, n, size) for i, (n, size) in enumerate(names_and_sizes))
    return Engine("aa" * 20, "pack", files, 0, 0.0, 0)


def test_next_episode_in_a_season_pack_ignores_samples_and_non_video() -> None:
    engine = _engine(
        ("Show.S01E01.mkv", 100),
        ("Show.S01E02.sample.mkv", 5),
        ("Show.S01E02.mkv", 100),
        ("Show.S01E02.nfo", 1),
    )
    nxt = next_episode(engine, 0)
    assert nxt is not None and nxt.index == 2


def test_next_episode_rolls_over_to_the_next_season() -> None:
    engine = _engine(("Show.S01E10.mkv", 100), ("Show.S02E01.mkv", 100))
    nxt = next_episode(engine, 0)
    assert nxt is not None and nxt.name == "Show.S02E01.mkv"


def test_no_next_episode_for_last_episode_or_movies() -> None:
    assert next_episode(_engine(("Show.S01E10.mkv", 100)), 0) is None
    assert next_episode(_engine(("Movie.2023.mkv", 100)), 0) is None
