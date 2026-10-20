"""The one typed view of the process environment.

Every field is required: a missing or invalid value fails boot instead of falling back
to a silent default. Values come from infra/env/companion.env (+ .env.local) via mise.
"""

from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
LogFormat = Literal["json", "console"]


class Env(BaseSettings):
    model_config = SettingsConfigDict(frozen=True, extra="ignore", case_sensitive=False)

    stremio_server_url: AnyHttpUrl
    companion_host: str = Field(min_length=1)
    companion_port: int = Field(ge=1, le=65535)
    log_level: LogLevel
    log_format: LogFormat


def load_env() -> Env:
    # pydantic-settings populates required fields from the environment at runtime.
    return Env()  # pyright: ignore[reportCallIssue]
