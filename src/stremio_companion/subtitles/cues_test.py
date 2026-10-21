from stremio_companion.subtitles.cues import Cue, render_srt, wrap


def test_short_text_stays_on_one_line() -> None:
    assert wrap("Mulțumesc. Unde e Wendy?") == "Mulțumesc. Unde e Wendy?"


def test_long_text_splits_at_punctuation_not_inside_a_phrase() -> None:
    out = wrap("Mike e un jurnalist renumit, de sport, de fapt, și autor de cărți.")
    top, bottom = out.split("\n")
    assert top.endswith(",") and not top.endswith(" de")
    assert len(top) <= 42 and len(bottom) <= 42


def test_render_srt_orders_cues_and_formats_times() -> None:
    srt = render_srt([Cue(65.5, 67.25, "Doi"), Cue(1.0, 2.0, "Unu")])
    assert srt == "1\n00:00:01,000 --> 00:00:02,000\nUnu\n\n2\n00:01:05,500 --> 00:01:07,250\nDoi\n"
