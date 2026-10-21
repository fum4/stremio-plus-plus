# Noisy third-party loggers capped at WARNING so INFO stays about our own events.
QUIET_LOGGERS = ("httpx", "httpcore", "uvicorn.access")
