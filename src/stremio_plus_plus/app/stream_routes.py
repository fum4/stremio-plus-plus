"""The Stremio++ stream entry and the HLS it plays: video repackaged untouched, subtitles inside
the stream, switched on and off from the player's subtitle menu (subtitle_switch.py)."""

import asyncio
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response

from stremio_plus_plus.app.addon import require_token, services_of
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.stream import playlists
from stremio_plus_plus.stream.constants import SEGMENT_S
from stremio_plus_plus.stream.media import UnsupportedMediaError
from stremio_plus_plus.stream.producer import segment_count
from stremio_plus_plus.stream.session import SegmentUnavailableError, Session
from stremio_plus_plus.subtitles.constants import LANG
from stremio_plus_plus.watch.events import FileRequested

log = structlog.get_logger()
router = APIRouter(prefix="/{token}", dependencies=[Depends(require_token)])
M3U8 = "application/vnd.apple.mpegurl"
VTT_WAIT_S = 4.0  # subtitles on but this segment's lines not generated yet: wait a little


@router.get("/stream/{kind}/{item_id}.json")
async def stream(request: Request, kind: str, item_id: str) -> dict[str, Any]:
    services = services_of(request)
    offer = await services.picker.pick(kind, item_id)
    if offer is None:
        return {"streams": []}
    env = services.env
    c = offer.candidate
    details = " · ".join(
        part
        for part in (
            f"{c.height}p" if c.height else "",
            f"{c.seeders} seeds" if c.seeders else "",
            "debrid" if c.url else "",
            c.addon,
        )
        if part
    )
    base = f"https://{env.addon_domain}:{env.addon_https_port}/{env.addon_token}"
    return {
        "streams": [
            {
                "name": "Stremio++",
                "title": f"{c.filename}\n{details}",
                "url": f"{base}/hls/{offer.key}/master.m3u8",
                "behaviorHints": {"bingeGroup": "stremio-plus-plus", "notWebReady": False},
            }
        ]
    }


async def _session(services: Services, key: str) -> Session:
    session = services.sessions.get(key)
    if session is None:
        source = await services.picker.resolve(key)
        if source is None:
            raise HTTPException(status_code=404)
        services.sessions.offer(source)
        session = services.sessions.get(key)
        assert session is not None
        services.subtitles.ensure(
            source.info_hash,
            source.file_index,
            source.file_name,
            source.file_length,
            url=None if source.url.startswith(services.env.server_base) else source.url,
        )
    try:
        await session.media()
    except UnsupportedMediaError as e:
        log.warning("stream_unsupported", file=session.source.file_name, reason=str(e))
        raise HTTPException(status_code=415) from None
    return session


@router.get("/hls/{key}/master.m3u8")
async def master(request: Request, key: str) -> Response:
    session = await _session(services_of(request), key)
    return Response(playlists.master(await session.media(), LANG), media_type=M3U8)


@router.get("/hls/{key}/video.m3u8")
async def video_playlist(request: Request, key: str) -> Response:
    session = await _session(services_of(request), key)
    return Response(playlists.video(await session.media()), media_type=M3U8)


@router.get("/hls/{key}/subs.m3u8")
async def subtitle_playlist(request: Request, key: str) -> Response:
    session = await _session(services_of(request), key)
    return Response(playlists.subtitles(await session.media()), media_type=M3U8)


@router.get("/hls/{key}/v{index}.ts")
async def video_segment(request: Request, key: str, index: int) -> FileResponse:
    services = services_of(request)
    session = await _session(services, key)
    try:
        path = await session.segment(index)
    except IndexError:
        raise HTTPException(status_code=404) from None
    except SegmentUnavailableError as e:
        log.warning("stream_segment_unavailable", file=session.source.file_name, reason=str(e))
        raise HTTPException(status_code=503) from None
    if abs(index - session.last_reported) >= REPORT_EVERY:  # every ~30 s, and at once on a seek
        session.last_reported = index
        # In the background: the handlers ask the busy streaming server things, the TV waits.
        task = asyncio.create_task(_report_playhead(services, session, index))
        _reports.add(task)
        task.add_done_callback(_reports.discard)
    return FileResponse(path, media_type="video/mp2t")


_reports: set[asyncio.Task[None]] = set()
REPORT_EVERY = 5  # segments (~30 s): pins and the subtitle playhead need no finer grain


async def _report_playhead(services: Services, session: Session, index: int) -> None:
    """Our reads are tagged, so the log tracker never sees this file played: tell the
    playback handlers (pins, next-episode prefetch, subtitle playhead) ourselves."""
    source = session.source
    media = await session.media()
    fraction = min(index * SEGMENT_S / max(media.duration_s, 1.0), 1.0)
    event = FileRequested(source.info_hash, source.file_index, int(fraction * source.file_length))
    for handler in services.playback_handlers:
        try:
            await handler(event)
        except Exception:
            log.exception("handler_failed", handler=getattr(handler, "__qualname__", "?"))


@router.get("/hls/{key}/s{index}.vtt")
async def subtitle_segment(request: Request, key: str, index: int) -> Response:
    services = services_of(request)
    session = await _session(services, key)
    media = await session.media()
    if not 0 <= index < segment_count(media.duration_s):
        raise HTTPException(status_code=404)
    start, end = playlists.segment_window(index)
    session.served_vtt(index)
    cues: list[tuple[float, float, str]] = []
    if session.subtitles_on:
        source = session.source
        waited = 0.0
        while True:
            all_cues = services.subtitles.cues(source.info_hash, source.file_index)
            cues = [(c.start, c.end, c.text) for c in all_cues if start <= c.start < end]
            covered = any(s <= start and end <= e for s, e in _spans(services, session))
            if cues or covered or waited >= VTT_WAIT_S:
                break
            await asyncio.sleep(0.5)
            waited += 0.5
    return Response(playlists.vtt(media, cues), media_type="text/vtt; charset=utf-8")


def _spans(services: Services, session: Session) -> list[tuple[float, float]]:
    return services.subtitle_store.spans(session.source.info_hash, session.source.file_index)
