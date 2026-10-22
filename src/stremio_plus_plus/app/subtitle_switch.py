"""The player's subtitle menu drives the subtitles inside our HLS stream.

The menu can't see in-stream subtitles, so "Romanian (AI)" there is a switch: the player
fetching that track tells us to fill the subtitle segments from now on. The segments it has
already buffered went out empty, so the track it fetched carries exactly those lines and
nothing after them: they show at once, never twice. Picking any other addon's track shows up
in the streaming server's log (watch/events.py SubtitleFetched) and switches ours off.
Stremio's own "Off" makes no request at all and can't be seen.
"""

import asyncio

import structlog
from fastapi.responses import PlainTextResponse

from stremio_plus_plus.app.services import Services
from stremio_plus_plus.stream.session import Session
from stremio_plus_plus.subtitles.cues import Cue, render_srt
from stremio_plus_plus.subtitles.scheduler import merged
from stremio_plus_plus.watch.events import Event, SubtitleFetched

log = structlog.get_logger()
OWN_TRACK_PATH = "/srt/"
# server.js answers 500 for a track without cues; this one shows nothing.
INVISIBLE = Cue(0.0, 0.01, "\u200b")
SRT = "application/x-subrip; charset=utf-8"


def _covered(services: Services, session: Session, start: float, end: float) -> bool:
    spans = merged(
        services.subtitle_store.spans(session.source.info_hash, session.source.file_index)
    )
    return any(s <= start and end <= e for s, e in spans)


async def switch_on(services: Services, session: Session, budget_s: float) -> PlainTextResponse:
    """`budget_s`: what's left of the proxy's patience for this fetch (it gives up at ~10 s)."""
    source = session.source
    session.subtitles_on = True
    services.subtitles.want(source.info_hash, source.file_index)
    # Exactly the subtitle segments buffered since the last seek, which went out empty.
    start, until = session.vtt_run_start, session.vtt_served_until
    waited = 0.0
    while until > start and not _covered(services, session, start, until) and waited < budget_s:
        await asyncio.sleep(0.5)
        waited += 0.5
    cues = [
        c
        for c in services.subtitles.cues(source.info_hash, source.file_index)
        if start <= c.start < until
    ]
    log.info(
        "stream_subtitles_on",
        file=source.file_name,
        bridged_until_s=round(until, 1),
        cues=len(cues),
        waited_s=waited,
    )
    return PlainTextResponse(render_srt(cues or [INVISIBLE]), media_type=SRT)


class SubtitleSwitch:
    """Tracker handler: another track picked in the menu switches our in-stream lines off."""

    def __init__(self, services: Services) -> None:
        self._services = services

    async def __call__(self, event: Event) -> None:
        if not isinstance(event, SubtitleFetched) or OWN_TRACK_PATH in event.source_url:
            return
        for session in self._services.sessions.live():
            if session.subtitles_on:
                session.subtitles_on = False
                log.info("stream_subtitles_off", file=session.source.file_name)
