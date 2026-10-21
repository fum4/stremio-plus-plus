from stremio_plus_plus.subtitles.scheduler import chunk_count, next_chunk


def test_chunk_count_rounds_up() -> None:
    assert chunk_count(3000, 120) == 25
    assert chunk_count(121, 120) == 2
    assert chunk_count(0, 120) == 1


def test_starts_at_the_playhead_then_ahead_then_back_fills() -> None:
    order: list[int] = []
    done: set[int] = set()
    while (nxt := next_chunk(done, 6, playhead_chunk=3)) is not None:
        order.append(nxt)
        done.add(nxt)
    assert order == [3, 4, 5, 2, 1, 0]


def test_skips_chunks_already_stored_and_clamps_the_playhead() -> None:
    assert next_chunk({0, 1}, 3, playhead_chunk=0) == 2
    assert next_chunk(set(), 3, playhead_chunk=99) == 2
    assert next_chunk({0, 1, 2}, 3, playhead_chunk=1) is None
