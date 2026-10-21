"""Pick the dialogue track and pull mono 16 kHz audio for one chunk straight from the server."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import numpy.typing as npt

from stremio_companion.subtitles.constants import AUDIO_TIMEOUT_S, SAMPLE_RATE

Audio = npt.NDArray[np.float32]
# Torrent content is untrusted: a crafted "video" (e.g. a playlist) must not reach local files.
_PROTOCOLS = ("-protocol_whitelist", "http,tcp")


@dataclass(frozen=True)
class AudioTrack:
    stream: int  # ordinal among the file's audio streams (ffmpeg `0:a:<n>`)
    center: bool  # 5.1+: dialogue lives in the centre channel (13.7 % vs 30.9 % WER on a downmix)
    duration_s: float


def choose_track(probe: dict[str, Any]) -> AudioTrack | None:
    streams = cast(list[dict[str, Any]], probe.get("streams") or [])
    if not streams:
        return None

    def rank(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int]:
        _, s = item
        tags = cast(dict[str, str], s.get("tags") or {})
        commentary = "comment" in tags.get("title", "").lower()
        english = tags.get("language", "").lower() in ("eng", "en")
        default = bool(cast(dict[str, int], s.get("disposition") or {}).get("default"))
        return (int(commentary), int(not english), int(not default))

    ordinal, stream = min(enumerate(streams), key=rank)
    layout = str(stream.get("channel_layout") or "").upper()
    center = (
        "FC" in layout
        or "5.1" in layout
        or "7.1" in layout
        or int(stream.get("channels") or 2) >= 6
    )
    duration = float(cast(dict[str, Any], probe.get("format") or {}).get("duration") or 0)
    return AudioTrack(ordinal, center, duration)


async def _run(*argv: str, timeout_s: float) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout_s)
    except TimeoutError:
        proc.kill()  # partial-torrent reads can idle forever without a wall-clock limit
        await proc.wait()
        raise
    return out


async def probe(url: str) -> AudioTrack | None:
    out = await _run(
        "ffprobe",
        *_PROTOCOLS,
        "-v",
        "error",
        "-rw_timeout",
        "60000000",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=channels,channel_layout:stream_tags=language,title:stream_disposition=default:format=duration",
        "-of",
        "json",
        url,
        timeout_s=AUDIO_TIMEOUT_S,
    )
    return choose_track(json.loads(out or b"{}"))


async def read_chunk(url: str, track: AudioTrack, start_s: float, length_s: float) -> Audio:
    channel = ["-af", "pan=mono|c0=FC"] if track.center else ["-ac", "1"]
    out = await _run(
        "ffmpeg",
        *_PROTOCOLS,
        "-v",
        "error",
        "-rw_timeout",
        "120000000",
        "-ss",
        f"{start_s:.3f}",
        "-t",
        f"{length_s:.3f}",
        "-i",
        url,
        "-map",
        f"0:a:{track.stream}",
        "-vn",
        "-sn",
        "-dn",
        *channel,
        "-ar",
        str(SAMPLE_RATE),
        "-f",
        "s16le",
        "-",
        timeout_s=AUDIO_TIMEOUT_S,
    )
    return np.frombuffer(out, np.int16).astype(np.float32) / 32768.0
