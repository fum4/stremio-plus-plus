from itertools import pairwise

from stremio_plus_plus.subtitles.scheduler import Span, merged, next_window

DURATION = 3000.0


def _play(playhead: float, steps: int) -> list[Span]:
    """Simulate the viewer watching while windows are generated at the modelled cost."""
    covered: list[Span] = []
    order: list[Span] = []
    for _ in range(steps):
        window = next_window(covered, DURATION, playhead)
        assert window is not None
        order.append(window)
        covered.append(window)
        playhead += 8.0 + 0.3 * (window[1] - window[0])  # time the window took
    return order


def test_merged_joins_touching_and_overlapping_spans() -> None:
    assert merged([(10, 20), (0, 10), (15, 30), (40, 50)]) == [(0, 30), (40, 50)]


def test_a_fresh_selection_starts_where_the_viewer_will_be_and_grows() -> None:
    order = _play(100.0, 5)
    assert order[0] == (112.5, 127.5)  # 100 s playhead + ~12.5 s for a 15 s window
    lengths = [round(end - start) for start, end in order]
    assert lengths == [15, 23, 51, 120, 120]
    assert all(a[1] == b[0] for a, b in pairwise(order))  # contiguous


def test_windows_grow_while_the_viewer_is_paused_at_a_fresh_selection() -> None:
    # Regression: the skipped seconds before the first window made every step look "fresh".
    covered: list[Span] = []
    lengths: list[int] = []
    for _ in range(4):
        window = next_window(covered, DURATION, 0.0)
        assert window is not None
        covered.append(window)
        lengths.append(round(window[1] - window[0]))
    assert covered[0] == (12.5, 27.5)
    assert lengths == [15, 65, 120, 120]  # lead from 0 s: 27.5 s -> (27.5 - 8) / 0.3 ≈ 65 s


def test_every_window_is_done_before_the_viewer_reaches_it() -> None:
    playhead, covered = 600.0, list[Span]()
    for _ in range(12):
        window = next_window(covered, DURATION, playhead)
        assert window is not None
        playhead += 8.0 + 0.3 * (window[1] - window[0])
        assert playhead <= window[0] + 1e-6 or not covered  # the first one is aimed ahead
        covered.append(window)


def test_back_fills_the_gap_and_the_start_once_ahead_is_covered() -> None:
    covered: list[Span] = [(112.5, DURATION)]
    assert next_window(covered, DURATION, 100.0) == (0.0, 112.5)
    assert next_window([(0, 50), (112.5, DURATION)], DURATION, 100.0) == (50.0, 112.5)
    assert next_window([(0.0, DURATION)], DURATION, 100.0) is None


def test_near_the_end_the_window_stays_inside_the_file() -> None:
    window = next_window([], DURATION, DURATION - 5)
    assert window is not None
    assert window[1] <= DURATION
