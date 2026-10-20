import json
import logging

import pytest
import structlog

from stremio_companion.log.setup import configure_logging


def test_json_format_emits_one_parseable_object_per_event(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(level="INFO", fmt="json")
    structlog.get_logger().info("hello", answer=42)
    logging.getLogger("stdlib").warning("plain")
    lines = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert lines[0] | {"timestamp": None} == {
        "event": "hello",
        "answer": 42,
        "level": "info",
        "timestamp": None,
    }
    assert lines[1]["event"] == "plain"


def test_level_filters_lower_events(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level="WARNING", fmt="json")
    structlog.get_logger().info("dropped")
    assert capsys.readouterr().err == ""
