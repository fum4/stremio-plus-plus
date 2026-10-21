import json

import pytest

from stremio_plus_plus.subtitles.translators.base import TranslatorConfigError
from stremio_plus_plus.subtitles.translators.claude_cli import parse_cli_output


def test_parse_cli_output_reads_structured_output() -> None:
    out = json.dumps({"structured_output": {"cues": [{"id": 1, "ro": "Salut."}]}})
    assert parse_cli_output(out) == {"cues": [{"id": 1, "ro": "Salut."}]}
    assert parse_cli_output("not json") is None


def test_parse_cli_output_reports_a_logged_out_cli() -> None:
    out = json.dumps({"is_error": True, "result": "Invalid API key · Please run /login"})
    with pytest.raises(TranslatorConfigError):
        parse_cli_output(out)
