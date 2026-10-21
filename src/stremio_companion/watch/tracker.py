"""Turn the server log into playback events and fan them out to the feature handlers."""

from collections.abc import AsyncIterator, Awaitable, Callable, Sequence

import structlog

from stremio_companion.watch.events import Event, parse_line

Handler = Callable[[Event], Awaitable[None]]
log = structlog.get_logger()


async def run_tracker(lines: AsyncIterator[str], handlers: Sequence[Handler]) -> None:
    async for line in lines:
        event = parse_line(line)
        if event is None:
            continue
        log.debug("playback_event", kind=type(event).__name__, **vars(event))
        for handler in handlers:
            try:
                await handler(event)
            except Exception:  # one broken feature must not stop the others from seeing events
                log.exception(
                    "handler_failed", handler=getattr(handler, "__qualname__", repr(handler))
                )
