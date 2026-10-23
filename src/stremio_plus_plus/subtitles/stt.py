"""Speech-to-text: Whisper large-v3-turbo on MLX (Apple Silicon)."""

import asyncio
from collections.abc import Callable
from typing import Any, Protocol, cast

import numpy as np

from stremio_plus_plus.config.settings import SpeechSettings
from stremio_plus_plus.subtitles.audio import Audio
from stremio_plus_plus.subtitles.constants import SAMPLE_RATE
from stremio_plus_plus.subtitles.cues import Cue


class Transcriber(Protocol):
    async def transcribe(self, audio: Audio, offset_s: float) -> list[Cue]: ...


class WhisperMlx:
    """Every decoding option is explicit: mlx-whisper's CLI and API defaults differ, and the
    defaults hallucinate repetition loops (docs/research/benchmarks/tears-of-steel.md)."""

    def __init__(self, settings: Callable[[], SpeechSettings]) -> None:
        self._settings = settings  # read per chunk: follows config.toml edits
        self._lock = asyncio.Lock()  # one inference at a time on the GPU

    async def warm(self) -> None:
        """Load the model now: the first load takes ~10 s, which would otherwise land on the
        first subtitle window after every companion start."""
        await self.transcribe(np.zeros(SAMPLE_RATE, np.float32), 0.0)

    async def transcribe(self, audio: Audio, offset_s: float) -> list[Cue]:
        async with self._lock:
            result = await asyncio.to_thread(self._run, audio, self._settings())
        segments = cast(list[dict[str, Any]], result["segments"])
        return [
            Cue(offset_s + float(s["start"]), offset_s + float(s["end"]), str(s["text"]).strip())
            for s in segments
            if str(s["text"]).strip()
        ]

    def _run(self, audio: Audio, settings: SpeechSettings) -> dict[str, Any]:
        import mlx_whisper  # pyright: ignore[reportMissingTypeStubs]  # heavy; loaded on first use

        return cast(
            dict[str, Any],
            mlx_whisper.transcribe(  # pyright: ignore[reportUnknownMemberType]
                audio,
                path_or_hf_repo=settings.model,
                language=settings.source_language,
                task="transcribe",
                temperature=0.0,
                condition_on_previous_text=False,
                hallucination_silence_threshold=2.0,
                word_timestamps=True,
                verbose=None,
            ),
        )
