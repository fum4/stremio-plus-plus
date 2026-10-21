import json

from stremio_companion.subtitles.translate import build_prompt, parse_response


def test_prompt_numbers_lines_and_trims_context() -> None:
    prompt = build_prompt(["Hello.", "Bye."], [f"c{i}" for i in range(20)])
    assert prompt.endswith("Translate:\n1: Hello.\n2: Bye.")
    assert "c4\n" not in prompt and "c5\n" in prompt


def test_parse_response_requires_every_id() -> None:
    ok = json.dumps(
        {"structured_output": {"cues": [{"id": 2, "ro": "Pa."}, {"id": 1, "ro": "Salut."}]}}
    )
    assert parse_response(ok, 2) == ["Salut.", "Pa."]
    missing = json.dumps({"structured_output": {"cues": [{"id": 1, "ro": "Salut."}]}})
    assert parse_response(missing, 2) is None
    assert parse_response("not json", 1) is None
