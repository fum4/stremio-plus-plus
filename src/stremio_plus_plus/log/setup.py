"""Structured logging: structlog on top of stdlib logging, JSON in services, console in dev."""

import logging

import structlog
from structlog.processors import ExceptionRenderer
from structlog.tracebacks import ExceptionDictTransformer

from stremio_plus_plus.config.env import LogFormat, LogLevel
from stremio_plus_plus.log.constants import QUIET_LOGGERS
from stremio_plus_plus.log.hub import HUB


def configure_logging(level: LogLevel, fmt: LogFormat) -> None:
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback)
    )
    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        HUB.capture,  # the UI's log view (log/hub.py); passes events through unchanged
    ]
    # Exceptions become a structured "exception" field in JSON (pretty tracebacks on the console).
    # No frame locals in tracebacks: they'd carry whatever a failing call held (a password, a key).
    exceptions: list[structlog.types.Processor] = (
        [ExceptionRenderer(ExceptionDictTransformer(show_locals=False))] if fmt == "json" else []
    )
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                *exceptions,
                renderer,
            ],
        )
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
