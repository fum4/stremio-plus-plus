"""How companion log events read in the activity feed: event name → one plain sentence.

Returns None for events that aren't worth a line (they stay in the raw log). Errors of any
event become a "problem" line, so nothing that went wrong is invisible in the feed.
"""

import re
from dataclasses import dataclass
from typing import Any

from stremio_plus_plus.state.activity import Category


@dataclass(frozen=True)
class Line:
    category: Category
    kind: str
    title: str
    detail: str | None = None
    key: str | None = None  # coalesce repeats with the same key…
    within_s: float = 0.0  # …within this many seconds


def clock(seconds: float) -> str:
    s = int(max(0, seconds))
    h, m = divmod(s // 60, 60)
    return f"{h}:{m:02d}:{s % 60:02d}" if h else f"{m}:{s % 60:02d}"


_EPISODE = re.compile(
    r"^(?P<show>.+?)[ ._-]+(?:\(?(?:19|20)\d{2}\)?[ ._-]+)?(?P<ep>S\d{1,2}E\d{1,3})(?P<rest>.*)$",
    re.I,
)
_JUNK = re.compile(
    r"[ ._-]+(?:\(?(?:19|20)\d{2}\)?|480p|576p|720p|1080p|2160p|4k|web|web-?dl|webrip|bluray|"
    r"brrip|hdtv|nf|amzn|dsnp|hmax|atvp|hevc|x26[45]|h ?26[45]|ddp?5|aac|atmos|remux|proper).*$",
    re.I,
)


def pretty_name(name: object) -> str:
    """'East.of.Eden.2026.S01E04.Kate.1080p.NF.WEB-DL…mkv' → 'East of Eden · S01E04 · Kate'."""
    base = str(name or "").rsplit("/", 1)[-1]
    base = re.sub(r"\.(mkv|mp4|avi|m4v|mov|webm|ts)$", "", base, flags=re.I).replace(".", " ")
    if m := _EPISODE.match(base):
        title = _JUNK.sub("", " " + m["rest"]).strip(" -_")
        show = m["show"].strip()
        return f"{show} · {m['ep'].upper()}" + (f" · {title}" if title else "")
    return _JUNK.sub("", " " + base).strip() or base


_short = pretty_name


def companion_line(event: str, f: dict[str, Any], level: str) -> Line | None:
    match event:
        case "pinned":
            return Line(
                "downloads",
                "pin",
                "Keeping the file downloading, even while paused",
                key=f"pin:{f.get('info_hash')}:{f.get('file_index')}",
                within_s=3600,
            )
        case "released" if f.get("reason") == "complete":
            return Line(
                "downloads",
                "complete",
                "Fully downloaded",
                key=f"rel:{f.get('info_hash')}:{f.get('file_index')}",
                within_s=3600,
            )
        case "released":
            return None  # torrent closed or shutting down (older logs: no reason): not news
        case "prefetch_next_episode":
            return Line(
                "downloads",
                "prefetch",
                "Getting the next episode ready",
                _short(f.get("next")),
                key=f"pre:{f.get('next')}",
                within_s=3600,
            )
        case "prefetch_skipped_low_disk":
            return Line(
                "problem",
                "disk",
                "Next episode not prefetched: disk almost full",
                f"{f.get('free_gb')} GB free",
            )
        case "subtitles_prepared":
            return Line(
                "subtitles",
                "prepared",
                "Audio found, generating Romanian subtitles",
                f"{_short(f.get('file'))} · {clock(float(f.get('duration_s') or 0))} long",
            )
        case "subtitles_reused_from_same_video":
            return Line(
                "subtitles", "reused", "Subtitles reused from the same video", _short(f.get("file"))
            )
        case "srt_served":
            return Line(
                "playback",
                "srt",
                "The TV loaded the subtitles",
                f"{f.get('cues')} lines"
                + (f", up to {clock(float(str(f['until_s'])))}" if f.get("until_s") else ""),
                key=f"srt:{f.get('info_hash')}:{f.get('file_index')}",
                within_s=300,
            )
        case "stremio_account_connected":
            return Line("system", "account", "Stremio account connected")
        case "stremio_account_disconnected":
            return Line("system", "account", "Stremio account disconnected")
        case "stremio_addon_installed":
            return Line(
                "system",
                "addon",
                "Stremio++ installed in your Stremio account",
                "first in the list",
            )
        case "stremio_addon_kept_first":
            detail = (
                "its address changed too"
                if f.get("repointed")
                else f"it was number {int(str(f.get('was_at') or 0)) + 1}"
            )
            return Line(
                "system",
                "addon",
                "Moved Stremio++ back to the top of your addons",
                detail,
                key="kept_first",
                within_s=3600,
            )
        case "stremio_addon_keep_failed":
            return Line(
                "problem",
                "addon",
                "Couldn't check the addon order in your Stremio account",
                str(f.get("error")),
                key="keep_failed",
                within_s=3600,
            )
        case "settings_reloaded":
            return Line("system", "settings", "Settings changed", "config.toml was edited")
        case "settings_invalid_keeping_last_good":
            return Line("problem", "settings", "config.toml has an error", str(f.get("error")))
        case "companion_started":
            return Line("system", "start", "stremio++ started")
        case "https_addon_serving" | "https_addon_certificate_reloaded" | "stremio_cert_renewed":
            return Line(
                "system",
                "https",
                "Addon certificate ready",
                str(f.get("domain")),
                key="https",
                within_s=86400,
            )
        case "tv_paired":
            return Line("system", "tv", "Paired with the TV", str(f.get("target")))
        case "setup_completed":
            return Line("system", "setup", "Setup finished")
        case "setup_server_configured":
            return Line(
                "system",
                "setup",
                "Streaming server set up for the TV",
                f"HTTPS for {f.get('remote_https')}",
            )
        case "whisper_model_downloaded":
            return Line("system", "model", "Speech model downloaded", str(f.get("model")))
        case "subtitles_no_audio":
            return Line("problem", "subtitles", "No audio track found", _short(f.get("file")))
        case "subtitle_window_failed":
            return Line(
                "problem",
                "subtitles",
                "A subtitle window failed (retried later)",
                _short(f.get("file")),
                key=f"fail:{f.get('file')}",
                within_s=600,
            )
        case "translate_failed_keeping_original":
            return Line(
                "problem",
                "translator",
                "The translator's reply was unusable",
                "those lines stayed in English",
                key="translate_failed",
                within_s=600,
            )
        case "translator_hourly_cap_reached":
            return Line(
                "problem",
                "translator",
                "Hourly translator cap reached",
                f"{f.get('calls')} calls in the last hour",
                key="cap",
                within_s=3600,
            )
        case _ if level in {"error", "critical"}:
            return Line(
                "problem",
                "error",
                event.replace("_", " ").capitalize(),
                str(f["error"])[:300] if f.get("error") else "details in Raw logs",
                key=f"err:{event}",
                within_s=600,
            )
        case _:
            return None
