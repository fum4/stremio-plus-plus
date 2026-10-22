"""The translator providers the settings can name, what the UI shows for each, and the switch that
rebuilds the backend whenever `config.toml` / `secrets.toml` change (no restart)."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from stremio_plus_plus.config.settings import Secrets, TranslatorProvider, TranslatorSettings
from stremio_plus_plus.config.settings_file import SettingsFile
from stremio_plus_plus.subtitles.translators.anthropic_api import AnthropicBackend
from stremio_plus_plus.subtitles.translators.base import (
    ATTEMPTS,
    Backend,
    HourlyCap,
    LlmTranslator,
    TranslatorStats,
)
from stremio_plus_plus.subtitles.translators.claude_cli import ClaudeCliBackend
from stremio_plus_plus.subtitles.translators.prompt import system_prompt


@dataclass(frozen=True)
class ModelOption:
    id: str
    label: str
    note: str


@dataclass(frozen=True)
class ProviderInfo:
    id: TranslatorProvider
    label: str
    description: str
    secret: str | None  # the Secrets field it needs, if any
    models: tuple[ModelOption, ...]


CLAUDE_MODELS = (
    ModelOption("claude-haiku-5-5", "Claude Haiku 5.5", "Fast and cheap; the default"),
    ModelOption("claude-sonnet-5-5", "Claude Sonnet 5.5", "More natural phrasing, slower"),
    ModelOption("claude-opus-5-5", "Claude Opus 5.5", "Best quality, priciest"),
)
PROVIDERS: dict[TranslatorProvider, ProviderInfo] = {
    "claude-cli": ProviderInfo(
        "claude-cli",
        "Claude subscription",
        "Uses the claude CLI logged in on this machine. Personal use of your own plan.",
        None,
        CLAUDE_MODELS,
    ),
    "anthropic": ProviderInfo(
        "anthropic",
        "Anthropic API",
        "Pay-as-you-go with your own API key from console.anthropic.com.",
        "anthropic_api_key",
        CLAUDE_MODELS,
    ),
}


def build_backend(settings: TranslatorSettings, secrets: Secrets, claude_bin: Path) -> Backend:
    match settings.provider:
        case "claude-cli":
            return ClaudeCliBackend(claude_bin, settings.model, settings.timeout_s)
        case "anthropic":
            return AnthropicBackend(secrets.anthropic_api_key, settings.model, settings.timeout_s)


class ConfiguredTranslator:
    """The `Translator` the subtitle jobs hold: follows the settings file as it changes."""

    def __init__(self, settings_file: SettingsFile, claude_bin: Path) -> None:
        self._file = settings_file
        self._claude_bin = claude_bin
        self.stats = TranslatorStats()
        self._cap = HourlyCap(self._settings.max_calls_per_hour)
        self._lock = asyncio.Lock()
        self._key: tuple[TranslatorSettings, Secrets] | None = None
        self._current: LlmTranslator | None = None

    @property
    def _settings(self) -> TranslatorSettings:
        return self._file.settings.subtitles.translator

    @property
    def calls_last_hour(self) -> int:
        return self._cap.used()

    @property
    def cap_reached(self) -> bool:
        return self._cap.used() >= self._cap.limit

    def build_test(self, settings: TranslatorSettings, secrets: Secrets) -> LlmTranslator:
        """A standalone translator for the UI's "test" button: its own tiny cap (never waits on or
        spends the jobs' hourly budget) and its own lock (a click doesn't queue behind a chunk)."""
        backend = build_backend(settings, secrets, self._claude_bin)
        return LlmTranslator(
            backend,
            HourlyCap(ATTEMPTS),
            settings.context_cues,
            TranslatorStats(),
            system=system_prompt(settings.style),
        )

    async def translate(self, lines: list[str], context: list[str]) -> list[str]:
        key = (self._settings, self._file.secrets)
        if self._current is None or key != self._key:
            self._key = key
            self._cap.limit = key[0].max_calls_per_hour
            backend = build_backend(key[0], key[1], self._claude_bin)
            self._current = LlmTranslator(
                backend,
                self._cap,
                key[0].context_cues,
                self.stats,
                self._lock,
                system=system_prompt(key[0].style),
            )
        return await self._current.translate(lines, context)
