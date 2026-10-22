"""Pick the release to play: on the laptop already > same release as the last episode >
playable on the TV > highest resolution up to the preference > most seeders."""

import math
from collections.abc import Iterable

from stremio_plus_plus.sources.candidates import Candidate
from stremio_plus_plus.sources.constants import MAX_HEIGHT


def _score(
    c: Candidate, local: dict[str, float], last_group: str | None, max_height: int
) -> tuple[float, ...]:
    within = 0 < c.height <= max_height
    return (
        float(c.playable),
        float(not c.dolby_vision),
        local.get(c.info_hash or "", 0.0),  # fraction already downloaded
        float(bool(last_group) and c.binge_group == last_group),
        float(c.url is not None),  # debrid links start instantly and never stall on peers
        float(within),
        float(c.height if within else -c.height),
        math.log1p(c.seeders),
    )


def dedupe(candidates: Iterable[Candidate]) -> list[Candidate]:
    seen: set[tuple[str | None, int | None, str | None]] = set()
    out: list[Candidate] = []
    for c in candidates:
        key = (c.info_hash, c.file_index, c.url)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def rank(
    candidates: Iterable[Candidate],
    local: dict[str, float] | None = None,
    last_group: str | None = None,
    max_height: int = MAX_HEIGHT,
) -> list[Candidate]:
    pool = dedupe(candidates)
    return sorted(pool, key=lambda c: _score(c, local or {}, last_group, max_height), reverse=True)
