"""Subtitle cues: timing, Romanian line wrapping, SRT rendering."""

import re
from dataclasses import dataclass

from stremio_plus_plus.subtitles.constants import MAX_LINE_CHARS, MAX_LINES

_BREAK_AFTER = re.compile(r"[,.;:!?\u2026\u2013-]$")  # incl. ellipsis and en dash


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def wrap(text: str, width: int = MAX_LINE_CHARS, max_lines: int = MAX_LINES) -> str:
    """Fit a cue on ≤ max_lines lines; when it needs two, split at the most balanced point,
    preferring right after punctuation and never between two short words of a phrase."""
    words = text.split()
    if len(" ".join(words)) <= width or len(words) < 2:
        return " ".join(words)
    best: tuple[float, int] | None = None
    for i in range(1, len(words)):
        top, bottom = " ".join(words[:i]), " ".join(words[i:])
        overflow = max(0, len(top) - width) + max(0, len(bottom) - width)
        score = overflow * 10 + abs(len(top) - len(bottom))
        if _BREAK_AFTER.search(words[i - 1]):
            score -= 8
        if len(words[i - 1]) <= 2:  # don't leave "de", "și", "a" dangling at a line end
            score += 6
        if best is None or score < best[0]:
            best = (score, i)
    assert best is not None
    split = best[1]
    lines = [" ".join(words[:split]), " ".join(words[split:])]
    return "\n".join(lines[:max_lines])


def _ts(t: float) -> str:
    ms = round(max(t, 0.0) * 1000)
    return f"{ms // 3_600_000:02}:{ms // 60_000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def render_srt(cues: list[Cue]) -> str:
    blocks = [
        f"{n}\n{_ts(c.start)} --> {_ts(c.end)}\n{wrap(c.text)}\n"
        for n, c in enumerate(sorted(cues, key=lambda c: c.start), 1)
    ]
    return "\n".join(blocks)
