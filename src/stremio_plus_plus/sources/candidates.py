"""Turn other addons' stream entries into comparable candidates.

Torrent addons (Torrentio, ThePirateBay+, …) describe each release only in free text, e.g.
name "Torrentio\\n4k" and title "Show.S01E03.2160p…\\n👤 120 💾 3.3 GB ⚙️ ThePirateBay".
"""

import re
from dataclasses import dataclass, field
from typing import Any, cast

from stremio_plus_plus.sources.constants import (
    DOLBY_VISION,
    ENGLISH_FLAGS,
    FOREIGN_WORDS,
    RESOLUTIONS,
    UNPLAYABLE,
)

_SEEDERS = re.compile(r"👤\s*(\d+)")
_SIZE = re.compile(r"💾\s*([\d.]+)\s*(GB|MB)", re.IGNORECASE)
_SEEDS_WORD = re.compile(r"(?:seeds?|seeders?)\W*(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class Candidate:
    addon: str
    text: str  # name + title, lowercased, for the heuristics
    filename: str
    info_hash: str | None = None  # torrent …
    file_index: int | None = None
    trackers: tuple[str, ...] = ()
    url: str | None = None  # … or a direct (debrid) link
    binge_group: str | None = None
    seeders: int = 0
    size_bytes: int = 0
    height: int = 0
    dolby_vision: bool = False
    playable: bool = True
    english: bool = True
    raw: dict[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)


_FLAG = re.compile("[\U0001f1e6-\U0001f1ff]{2}")


def _height(text: str) -> int:
    words = set(re.split(r"[^a-z0-9]+", text))
    return next((h for word, h in RESOLUTIONS if word in words), 0)


def _english(text: str) -> bool:
    flags = _FLAG.findall(text)
    if flags and not any(f in ENGLISH_FLAGS for f in flags):
        return False
    return not any(word in text for word in FOREIGN_WORDS)


def _size(text: str) -> int:
    if m := _SIZE.search(text):
        return int(float(m[1]) * (1 << 30 if m[2].upper() == "GB" else 1 << 20))
    return 0


def parse(addon: str, stream: dict[str, Any]) -> Candidate | None:
    hints = cast(dict[str, Any], stream.get("behaviorHints") or {})
    name = str(stream.get("name") or "")
    title = str(stream.get("title") or stream.get("description") or "")
    filename = str(hints.get("filename") or title.split("\n", 1)[0])
    text = f" {name}\n{title}\n{filename} ".lower()
    info_hash = str(stream.get("infoHash") or "").lower() or None
    url = str(stream.get("url") or "") or None
    if info_hash is None and (url is None or not url.startswith(("http://", "https://"))):
        return None  # YouTube ids, external links, …
    sources = cast(list[str], stream.get("sources") or [])
    seeders = _SEEDERS.search(text) or _SEEDS_WORD.search(text)
    return Candidate(
        addon=addon,
        text=text,
        filename=filename,
        info_hash=info_hash,
        file_index=int(stream["fileIdx"]) if stream.get("fileIdx") is not None else None,
        trackers=tuple(s for s in sources if isinstance(s, str)),  # pyright: ignore[reportUnnecessaryIsInstance]
        url=None if info_hash else url,
        binge_group=str(hints["bingeGroup"]) if hints.get("bingeGroup") else None,
        seeders=int(seeders[1]) if seeders else 0,
        size_bytes=int(hints.get("videoSize") or 0) or _size(text),
        height=_height(f"{title}\n{filename}".lower()) or _height(name.lower()),
        dolby_vision=any(word in text for word in DOLBY_VISION) and "hdr10" not in text,
        playable=not any(word in text for word in UNPLAYABLE),
        english=_english(text),
        raw=stream,
    )
