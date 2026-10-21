"""`/api/logs` (raw: server + companion lines, redacted) and `/api/activity` (the timeline).

Both are polled by the UI with a cursor (`after` seq / `since` timestamp), so a poll only carries
what's new. LAN only, behind the same header + Host check as the rest of the admin API.
"""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from stremio_plus_plus.app.admin import require_ui
from stremio_plus_plus.app.services import Services
from stremio_plus_plus.log.hub import HUB

router = APIRouter(prefix="/api", dependencies=[Depends(require_ui)])
MAX_LINES = 5000


def _services(request: Request) -> Services:
    return request.app.state.services


@router.get("/logs")
async def logs(
    after: int = Query(0, ge=0), limit: int = Query(2000, ge=1, le=MAX_LINES)
) -> dict[str, Any]:
    entries = HUB.since(after, limit)
    return {
        "entries": [asdict(e) for e in entries],
        "cursor": entries[-1].seq if entries else after,
    }


@router.get("/activity")
async def activity(
    request: Request,
    since: float = Query(0.0, ge=0),
    before: int | None = Query(None, ge=1),
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, Any]:
    store = _services(request).activity
    items = store.before(before, limit) if before else store.changed_since(since, limit)
    return {"items": [asdict(i) for i in items]}
