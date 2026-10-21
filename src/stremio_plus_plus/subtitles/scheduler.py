"""Which window of the video to subtitle next, and how long it should be.

One window of L seconds costs about T(L) = STEP_FIXED_S + STEP_PER_S·L (audio read, Whisper,
one Claude call; measured on the M4 host, docs/research/subtitle-latency.md). A window has to be
done before the viewer reaches it, so with `lead` seconds already covered ahead of the playhead
the next one can be at most (lead - STEP_FIXED_S) / STEP_PER_S long. Starting from
FIRST_WINDOW_S that grows 15 → 23 → 51 → 120 s, then stays at MAX_WINDOW_S. Lengths only
grow if FIRST_WINDOW_S > STEP_FIXED_S / (1 - STEP_PER_S) (~11 s): a shorter first window
never builds a lead.

With nothing covered at the playhead (a fresh selection, a seek) the first window starts where
the viewer will be when it's done, not where they are: its lines arrive on time instead of
already behind. The skipped seconds, and everything before the playhead, are back-filled once
the rest of the file is covered.
"""

from stremio_plus_plus.subtitles.constants import (
    FIRST_WINDOW_S,
    MAX_WINDOW_S,
    MIN_WINDOW_S,
    STEP_FIXED_S,
    STEP_PER_S,
)

Span = tuple[float, float]


def merged(spans: list[Span]) -> list[Span]:
    out: list[Span] = []
    for start, end in sorted(spans):
        if out and start <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def _covered_until(spans: list[Span], t: float) -> float:
    """End of the coverage that contains t (t itself if t isn't covered)."""
    for start, end in spans:
        if start <= t < end:
            return end
    return t


def _next_start_after(spans: list[Span], t: float, duration: float) -> float:
    return min([start for start, _ in spans if start > t] + [duration])


def _window_at(spans: list[Span], start: float, length: float, duration: float) -> Span:
    return start, min(start + length, _next_start_after(spans, start, duration))


def next_window(covered: list[Span], duration: float, playhead: float) -> Span | None:
    spans = merged(covered)
    playhead = min(max(playhead, 0.0), duration)
    aim = playhead + STEP_FIXED_S + STEP_PER_S * FIRST_WINDOW_S
    aim = min(aim, max(duration - FIRST_WINDOW_S, playhead))
    # Coverage ahead of the viewer starts at the playhead, or at a first window aimed past it
    # (the seconds skipped before that are back-filled later, not counted as a hole).
    ahead = [s for s, e in spans if s <= playhead < e] or [
        s for s, _ in spans if playhead < s <= aim + 0.5
    ]
    if not ahead:  # nothing ahead: aim where the viewer will be
        start = _covered_until(spans, aim)
        if start < duration:
            return _window_at(spans, start, FIRST_WINDOW_S, duration)
    else:
        end = _covered_until(spans, ahead[0])
        if end < duration:
            length = (end - playhead - STEP_FIXED_S) / STEP_PER_S
            return _window_at(spans, end, min(max(length, MIN_WINDOW_S), MAX_WINDOW_S), duration)
    return next_fill(spans, duration)  # back-fill once everything ahead is covered


def next_fill(covered: list[Span], duration: float) -> Span | None:
    """The first gap from the start of the file, in MAX_WINDOW_S windows."""
    spans = merged(covered)
    cursor = 0.0
    for start, stop in spans:
        if start - cursor > 0.5:
            return _window_at(spans, cursor, MAX_WINDOW_S, duration)
        cursor = max(cursor, stop)
    if duration - cursor > 0.5:
        return _window_at(spans, cursor, MAX_WINDOW_S, duration)
    return None
