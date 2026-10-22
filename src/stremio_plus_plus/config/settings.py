"""User settings: the typed shape of `config.toml` (CONFIG_DIR).

The file is the source of truth: people, agents and the UI all edit the same TOML. Every field
has a default, so a missing file or section means "the defaults", and an unknown key is an error
(a typo must not silently do nothing).
"""

from ipaddress import IPv4Address
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

TranslatorProvider = Literal["claude-cli", "anthropic"]
SpeechEngine = Literal["mlx-whisper"]
TvOs = Literal["samsung", "webos", "androidtv", "firetv"]


class _Section(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TranslatorSettings(_Section):
    provider: TranslatorProvider = "claude-cli"
    model: str = Field(default="claude-haiku-5-5", min_length=1)
    max_calls_per_hour: int = Field(default=120, ge=1, le=10_000)
    timeout_s: int = Field(default=180, ge=10, le=3600)
    context_cues: int = Field(default=15, ge=0, le=200)
    # Free-form style for the wording ("like a cowboy", "formal", …); the format rules still hold.
    style: str = Field(default="", max_length=2000)


class SpeechSettings(_Section):
    engine: SpeechEngine = "mlx-whisper"
    model: str = Field(default="mlx-community/whisper-large-v3-turbo", min_length=1)
    source_language: str = Field(default="en", min_length=2, max_length=3)


class SubtitleSettings(_Section):
    translator: TranslatorSettings = TranslatorSettings()
    speech: SpeechSettings = SpeechSettings()
    # Episodes after the playing one to generate whole, ahead of time (0 = off). Capped by
    # downloads.next_episodes: the audio comes from the downloaded file.
    next_episodes: int = Field(default=1, ge=0, le=20)


class DownloadSettings(_Section):
    min_free_gb: float = Field(default=3.0, ge=0.5, le=10_000)
    stale_after_days: float = Field(default=7.0, ge=0.5, le=3650)
    # Episodes after the playing one to download in advance, or "season": the rest of the season.
    next_episodes: Annotated[int, Field(ge=0, le=50)] | Literal["season"] = 1

    def lookahead(self, subtitles: int) -> tuple[int | None, int]:
        """(episodes to download, None = rest of the season; episodes to subtitle ahead)."""
        downloads = None if self.next_episodes == "season" else self.next_episodes
        return downloads, subtitles if downloads is None else min(subtitles, downloads)

    @property
    def min_free_bytes(self) -> int:
        return int(self.min_free_gb * 1024**3)

    @property
    def stale_after_s(self) -> float:
        return self.stale_after_days * 86400


class TvSettings(_Section):
    """A TV this host can control (tv/): found and paired by the setup, or written by hand."""

    host: IPv4Address | None = None
    os: TvOs | None = None  # which tv/ adapter; only samsung is verified on hardware


class StremioSettings(_Section):
    """What stremio++ does with a connected Stremio account (account/)."""

    keep_addon_first: bool = True  # Stremio lists streams in collection order


class Settings(_Section):
    subtitles: SubtitleSettings = SubtitleSettings()
    downloads: DownloadSettings = DownloadSettings()
    tv: TvSettings = TvSettings()
    stremio: StremioSettings = StremioSettings()


class Secrets(_Section):
    """`secrets.toml` (mode 0600, next to config.toml): never in config.toml, never sent back."""

    anthropic_api_key: str | None = None
    # The addon URL's secret path segment when ADDON_TOKEN isn't in the environment (host.py).
    addon_token: str | None = Field(default=None, min_length=24)
