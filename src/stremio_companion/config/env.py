"""The one typed view of the process environment.

Every field is required: a missing or invalid value fails boot instead of falling back
to a silent default. Values come from infra/env/companion.env (+ .env.local) via mise.
"""

from ipaddress import IPv4Address
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
LogFormat = Literal["json", "console"]


class Env(BaseSettings):
    model_config = SettingsConfigDict(frozen=True, extra="ignore", case_sensitive=False)

    stremio_server_url: AnyHttpUrl
    stremio_server_log: Path
    companion_host: str = Field(min_length=1)
    companion_port: int = Field(ge=1, le=65535)
    companion_data_dir: Path
    host_lan_ip: IPv4Address
    log_level: LogLevel
    log_format: LogFormat

    @field_validator("stremio_server_log", "companion_data_dir", mode="before")
    @classmethod
    def _expand_home(cls, value: object) -> object:
        return Path(value).expanduser() if isinstance(value, str) else value

    @property
    def server_base(self) -> str:
        return str(self.stremio_server_url).rstrip("/")


def load_env() -> Env:
    # pydantic-settings populates required fields from the environment at runtime.
    return Env()  # pyright: ignore[reportCallIssue]
