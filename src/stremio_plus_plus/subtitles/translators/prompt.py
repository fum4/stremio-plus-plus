"""What every translator backend sends and expects back: provider-neutral.

The model sees numbered lines only, never timings; the reply is a JSON object of `{id, ro}` cues
(enforced by the backend's structured-output feature, re-checked here).
"""

from typing import Any, cast

TASK = "You translate English TV subtitles into Romanian, with correct diacritics (ă â î ș ț). "
TONE = (
    "Write natural, idiomatic Romanian as a professional subtitler would: concise, colloquial "
    "where the speech is, keep names, keep profanity at the same strength. "
)
# A chosen style replaces TONE: next to "as a professional subtitler would" the model plays safe.
STYLE = (
    "Voice: the viewer chose a style for these subtitles. Apply it strongly and consistently to "
    "every line (word choice, slang, rhythm, attitude) so it is unmistakable, while keeping each "
    "line's meaning and keeping it short enough to read. The style: {style}\n"
)
FORMAT = (
    "You get numbered lines; return exactly one translation per id, same ids, no merging or "
    "splitting. Lines given as context are earlier, already-translated subtitles: use them only "
    "for continuity."
)


def system_prompt(style: str) -> str:
    voice = STYLE.format(style=style.strip()) if style.strip() else TONE
    return TASK + voice + FORMAT


SYSTEM_PROMPT = system_prompt("")
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "ro": {"type": "string"}},
                "required": ["id", "ro"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["cues"],
    "additionalProperties": False,
}


def build_prompt(lines: list[str], context: list[str], context_cues: int) -> str:
    ctx = "\n".join(context[-context_cues:]) if context_cues else ""
    body = "\n".join(f"{i}: {line}" for i, line in enumerate(lines, 1))
    return (
        f"Context (earlier subtitles, already translated):\n{ctx}\n\n" if ctx else ""
    ) + f"Translate:\n{body}"


def parse_cues(output: dict[str, Any] | None, expected: int) -> list[str] | None:
    """The translations in id order, or None unless every id 1..expected is present."""
    if not output:
        return None
    try:
        got = {
            int(c["id"]): str(c["ro"]) for c in cast(list[dict[str, Any]], output.get("cues") or [])
        }
    except KeyError, TypeError, ValueError:
        return None
    if all(i in got for i in range(1, expected + 1)):
        return [got[i] for i in range(1, expected + 1)]
    return None
