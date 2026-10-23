"""The one typed view of the process environment.

Every field is required: a missing or invalid value fails boot instead of falling back
to a silent default. Values come from infra/env/companion.env (+ .env.local) via mise.
This is the machine wiring; what a user tunes lives in config.toml (settings.py).
"""

from ipaddress import IPv4Address
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
LogFormat = Literal["json", "console"]
TvOs = Literal["samsung", "webos", "androidtv", "firetv"]


class Env(BaseSettings):
    model_config = SettingsConfigDict(frozen=True, extra="ignore", case_sensitive=False)

    stremio_server_url: AnyHttpUrl
    stremio_server_log: Path
    companion_host: str = Field(min_length=1)
    companion_port: int = Field(ge=1, le=65535)
    companion_data_dir: Path
    # config.toml + secrets.toml (settings_file.py): what the user tunes (by hand, agent or UI).
    config_dir: Path
    # The built admin UI (web/, `mise run ui:build`); served on the LAN port when present.
    ui_dir: Path
    host_lan_ip: IPv4Address
    tv_host: IPv4Address
    tv_os: TvOs  # which tv/ adapter controls the TV; only samsung is verified on hardware
    claude_cli: Path
    addon_domain: str = Field(min_length=1)
    addon_https_port: int = Field(ge=1, le=65535)
    # Secret path segment of the public addon URL (secrets/companion.env.age; repo-secrets exec).
    addon_token: str = Field(min_length=24, repr=False)
    log_level: LogLevel
    log_format: LogFormat

    @field_validator(
        "stremio_server_log", "companion_data_dir", "config_dir", "claude_cli", mode="before"
    )
    @classmethod
    def _expand_home(cls, value: object) -> object:
        return Path(value).expanduser() if isinstance(value, str) else value

    @property
    def tls_dir(self) -> Path:
        """lego's data dir: account + certificates for ADDON_DOMAIN."""
        return self.companion_data_dir / "tls"

    @property
    def server_base(self) -> str:
        return str(self.stremio_server_url).rstrip("/")


def load_env() -> Env:
    # pydantic-settings populates required fields from the environment at runtime.
    return Env()  # pyright: ignore[reportCallIssue]
