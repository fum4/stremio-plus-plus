"""HLS playlists for one session: a master with the video and a default-on subtitle rendition,
and VOD media playlists listing every segment up front (the player fetches each one lazily,
which is what lets subtitles change while the episode plays)."""

from stremio_plus_plus.stream.constants import MPEGTS_HZ, SEGMENT_S, TS_OFFSET_S, VTT_EMPTY
from stremio_plus_plus.stream.media import Media
from stremio_plus_plus.stream.producer import segment_count

SUBTITLE_NAME = "Stremio++"


def _durations(duration_s: float) -> list[float]:
    count = segment_count(duration_s)
    last = duration_s - (count - 1) * SEGMENT_S
    return [SEGMENT_S] * (count - 1) + [max(last, 0.1)]


def master(media: Media, language: str) -> str:
    bandwidth = 20_000_000 if media.height > 1100 else 8_000_000
    return (
        "#EXTM3U\n#EXT-X-VERSION:3\n"
        f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{SUBTITLE_NAME}",DEFAULT=YES,'
        f'AUTOSELECT=YES,FORCED=NO,LANGUAGE="{language}",URI="subs.m3u8"\n'
        f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={media.width}x{media.height},"
        f'CODECS="{media.video_tag},{media.audio_tag}",SUBTITLES="subs"\n'
        "video.m3u8\n"
    )


def _media_playlist(media: Media, name: str) -> str:
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{int(SEGMENT_S) * 3}",  # copied video: cuts drift to keyframes
        "#EXT-X-MEDIA-SEQUENCE:0",
        "#EXT-X-PLAYLIST-TYPE:VOD",
    ]
    for index, duration in enumerate(_durations(media.duration_s)):
        lines += [f"#EXTINF:{duration:.3f},", name.format(index=index)]
    return "\n".join([*lines, "#EXT-X-ENDLIST", ""])


def video(media: Media) -> str:
    return _media_playlist(media, "v{index}.ts")


def subtitles(media: Media) -> str:
    return _media_playlist(media, "s{index}.vtt")


def mpegts_origin(media: Media) -> int:
    """MPEG-TS timestamp of the source's time zero in our segments (cue times are relative)."""
    return round((media.start_s + TS_OFFSET_S) * MPEGTS_HZ)


def segment_window(index: int) -> tuple[float, float]:
    return index * SEGMENT_S, (index + 1) * SEGMENT_S


def vtt(media: Media, cues: list[tuple[float, float, str]]) -> str:
    out = VTT_EMPTY.format(mpegts=mpegts_origin(media))
    for start, end, text in cues:
        out += f"{_stamp(start)} --> {_stamp(end)}\n{text}\n\n"
    return out


def _stamp(seconds: float) -> str:
    ms = round(max(seconds, 0.0) * 1000)
    h, rest = divmod(ms, 3_600_000)
    m, rest = divmod(rest, 60_000)
    s, ms = divmod(rest, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
