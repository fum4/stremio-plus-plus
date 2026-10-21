import pytest

from stremio_plus_plus.downloads.episodes import next_episodes, parse_episode
from stremio_plus_plus.server.models import Engine, TorrentFile


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
    assert [f.index for f in next_episodes(engine, 0, 1)] == [2]


def test_next_episode_rolls_over_to_the_next_season() -> None:
    engine = _engine(("Show.S01E10.mkv", 100), ("Show.S02E01.mkv", 100))
    assert [f.name for f in next_episodes(engine, 0, 1)] == ["Show.S02E01.mkv"]


def test_no_next_episode_for_last_episode_or_movies() -> None:
    assert next_episodes(_engine(("Show.S01E10.mkv", 100)), 0, 1) == []
    assert next_episodes(_engine(("Movie.2023.mkv", 100)), 0, 1) == []


def test_n_episodes_or_the_rest_of_the_season() -> None:
    engine = _engine(
        ("Show.S01E03.mkv", 100),
        ("Show.S01E01.mkv", 100),
        ("Show.S01E02.mkv", 100),
        ("Show.S01E04.mkv", 100),
        ("Show.S02E01.mkv", 100),
    )

    def names(files: list[TorrentFile]) -> list[str]:
        return [f.name[5:11] for f in files]

    assert names(next_episodes(engine, 2, 2)) == ["S01E03", "S01E04"]
    assert names(next_episodes(engine, 2, 5)) == ["S01E03", "S01E04", "S02E01"]
    assert names(next_episodes(engine, 2, None)) == ["S01E03", "S01E04"]
    assert next_episodes(engine, 2, 0) == []
