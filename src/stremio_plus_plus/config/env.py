"""The one typed view of the process environment.

Wiring fields are required: a missing or invalid value fails boot instead of falling back to a
silent default. Values come from infra/env/companion.env (+ .env.local) via mise. The optional
fields are the owner's personal setup (own domain, a TV to control, an encrypted token); a fresh
install leaves them unset and gets the zero-config path (config/host.py, tls/stremio_cert.py).
This is the machine wiring; what a user tunes lives in config.toml (settings.py).
"""

from ipaddress import IPv4Address
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from stremio_plus_plus.config.settings import TvOs

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
LogFormat = Literal["json", "console"]


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
    # The streaming server's data dir (launchd APP_PATH): holds its stremio.rocks certificate.
    stremio_server_data_dir: Path
    # Applied to the server by the setup (POST /settings merges), plus remoteHttps = the LAN IP.
    stremio_server_settings: Path
    # Unset: detected from the default route (config/host.py).
    host_lan_ip: IPv4Address | None = None
    # A TV to control (tv/, `mise run tv`); wins over config.toml [tv]. Usually unset.
    tv_host: IPv4Address | None = None
    tv_os: TvOs | None = None  # which tv/ adapter; only samsung is verified on hardware
    claude_cli: Path
    # Unset: the addon is served under the streaming server's stremio.rocks certificate.
    addon_domain: str | None = Field(default=None, min_length=1)
    addon_https_port: int = Field(ge=1, le=65535)
    # Secret path segment of the addon URL. Unset: generated once into secrets.toml.
    addon_token: str | None = Field(default=None, min_length=24, repr=False)
    log_level: LogLevel
    log_format: LogFormat

    @field_validator(
        "host_lan_ip", "tv_host", "tv_os", "addon_domain", "addon_token", mode="before"
    )
    @classmethod
    def _empty_is_unset(cls, value: object) -> object:
        """`KEY=` in .env.local means "deliberately not set" (with-secrets.sh needs it set)."""
        return None if value == "" else value

    @field_validator(
        "stremio_server_log",
        "stremio_server_data_dir",
        "companion_data_dir",
        "config_dir",
        "claude_cli",
        mode="before",
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
