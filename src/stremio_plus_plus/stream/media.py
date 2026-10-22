"""Probe a source once and decide how to repackage it for the TV: video copied, audio copied
when the TV plays it inside HLS, converted to Dolby Digital otherwise."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, cast

from stremio_plus_plus.stream.constants import (
    COPY_AUDIO,
    FALLBACK_AUDIO_BITRATE,
    FALLBACK_AUDIO_CODEC,
    FALLBACK_AUDIO_MAX_CHANNELS,
    PROBE_TIMEOUT_S,
    VIDEO_CODECS,
)

# Torrent content is untrusted: a crafted "video" (e.g. a playlist) must not reach local files.
PROTOCOLS = ("-protocol_whitelist", "http,https,tcp,tls")


class UnsupportedMediaError(Exception):
    pass


@dataclass(frozen=True)
class Media:
    duration_s: float
    start_s: float  # the source's first timestamp; output timestamps are relative to it
    video_codec: str
    video_tag: str  # HLS CODECS entry, e.g. hvc1.2.4.L153.B0
    width: int
    height: int
    audio_index: int  # ordinal among the audio streams (ffmpeg `0:a:<n>`)
    audio_codec: str  # what the TV gets
    audio_tag: str
    audio_args: tuple[str, ...]  # ffmpeg codec options for that audio


def _audio_tag(codec: str) -> str:
    return {"ac3": "ac-3", "eac3": "ec-3", "mp3": "mp4a.40.34"}.get(codec, "mp4a.40.2")


def _video_tag(stream: dict[str, Any]) -> str:
    codec = str(stream.get("codec_name"))
    profile = str(stream.get("profile") or "")
    level = int(stream.get("level") or 0)
    if codec == "hevc":
        return f"hvc1.{2 if '10' in profile else 1}.4.L{level or 153}.B0"
    profiles = {"Baseline": 0x42, "Constrained Baseline": 0x42, "Main": 0x4D, "High": 0x64}
    return f"avc1.{profiles.get(profile, 0x64):02X}00{level or 40:02X}"


def _rank_audio(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int]:
    _, s = item
    tags = cast(dict[str, str], s.get("tags") or {})
    commentary = "comment" in tags.get("title", "").lower()
    english = tags.get("language", "").lower() in ("eng", "en")
    default = bool(cast(dict[str, int], s.get("disposition") or {}).get("default"))
    return (int(commentary), int(not english), int(not default))


def plan(probe: dict[str, Any]) -> Media:
    streams = cast(list[dict[str, Any]], probe.get("streams") or [])
    videos = [s for s in streams if s.get("codec_type") == "video" and s.get("codec_name")]
    video = next((v for v in videos if not v.get("disposition", {}).get("attached_pic")), None)
    if video is None or video["codec_name"] not in VIDEO_CODECS:
        raise UnsupportedMediaError(f"video codec {video and video.get('codec_name')}")
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not audios:
        raise UnsupportedMediaError("no audio")
    index, audio = min(enumerate(audios), key=_rank_audio)
    source_codec = str(audio.get("codec_name"))
    if source_codec in COPY_AUDIO:
        codec, args = source_codec, ("-c:a", "copy")
    else:
        channels = min(int(audio.get("channels") or 2), FALLBACK_AUDIO_MAX_CHANNELS)
        codec = FALLBACK_AUDIO_CODEC
        args = ("-c:a", codec, "-b:a", FALLBACK_AUDIO_BITRATE, "-ac", str(channels))
    fmt = cast(dict[str, Any], probe.get("format") or {})
    return Media(
        duration_s=float(fmt.get("duration") or 0),
        start_s=float(fmt.get("start_time") or 0),
        video_codec=str(video["codec_name"]),
        video_tag=_video_tag(video),
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        audio_index=index,
        audio_codec=codec,
        audio_tag=_audio_tag(codec),
        audio_args=args,
    )


async def run(*argv: str, timeout_s: float = PROBE_TIMEOUT_S) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout_s)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise
    return out


async def probe(url: str) -> Media:
    out = await run(
        "ffprobe", *PROTOCOLS, "-v", "error", "-show_format", "-show_streams", "-of", "json", url
    )
    return plan(json.loads(out or b"{}"))


async def keyframe_at(url: str, at_s: float) -> float:
    """Timestamp of the video keyframe an input seek to `at_s` lands on (at or before it)."""
    out = await run(
        "ffprobe", *PROTOCOLS, "-v", "error", "-read_intervals", f"{at_s}%+#1",
        "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0", url,
    )  # fmt: skip
    first = out.decode().split()
    return float(first[0].strip(",")) if first else at_s
