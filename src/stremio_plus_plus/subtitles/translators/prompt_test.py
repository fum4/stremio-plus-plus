from stremio_plus_plus.subtitles.translators.prompt import build_prompt, parse_cues


def test_prompt_numbers_lines_and_trims_context() -> None:
    prompt = build_prompt(["Hello.", "Bye."], [f"c{i}" for i in range(20)], context_cues=15)
    assert prompt.endswith("Translate:\n1: Hello.\n2: Bye.")
    assert "c4\n" not in prompt and "c5\n" in prompt


def test_prompt_without_context() -> None:
    assert build_prompt(["Hi."], ["c1"], context_cues=0) == "Translate:\n1: Hi."


def test_parse_cues_requires_every_id() -> None:
    ok = {"cues": [{"id": 2, "ro": "Pa."}, {"id": 1, "ro": "Salut."}]}
    assert parse_cues(ok, 2) == ["Salut.", "Pa."]
    assert parse_cues({"cues": [{"id": 1, "ro": "Salut."}]}, 2) is None
    assert parse_cues({"cues": [{"oops": 1}]}, 1) is None
    assert parse_cues(None, 1) is None
