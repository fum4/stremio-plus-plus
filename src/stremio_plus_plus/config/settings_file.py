"""`config.toml` + `secrets.toml` on disk: load, hot-reload on change, save without losing comments.

Hand and agent edits are first-class: the companion polls the files' mtimes and picks a change up
within seconds. A broken edit keeps the last good settings running and is reported (`error`), never
half-applied. Saves go through tomlkit so comments and key order survive, and are atomic.
"""

import os
import tomllib
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any, cast

import tomlkit
from pydantic import ValidationError
from tomlkit.exceptions import TOMLKitError

from stremio_plus_plus.config.settings import Secrets, Settings

TEMPLATE = """\
# stremio++ settings. Edit by hand, ask an agent, or use the UI (http://<host>:11471/).
# The companion reloads this file within a few seconds of a change; an invalid edit is ignored
# (the last good settings keep running) and shown in the UI. Secrets live in secrets.toml.

[subtitles.translator]
provider = "claude-cli"        # claude-cli (your Claude subscription) | anthropic (API key)
model = "claude-haiku-5-5"
max_calls_per_hour = 120       # hard cap, protects a subscription or a budget
timeout_s = 180
context_cues = 15              # earlier subtitles sent along for continuity
style = ""                     # optional: how the translation should sound, e.g. "like a cowboy"

[subtitles.speech]
engine = "mlx-whisper"         # Apple Silicon
model = "mlx-community/whisper-large-v3-turbo"
source_language = "en"

[downloads]
min_free_gb = 3                # never let downloads push the disk below this
stale_after_days = 7           # delete torrents nobody played for this long

[tv]                           # optional: a TV this Mac can control; the setup finds and pairs it
# host = "192.168.1.134"
# os = "samsung"               # samsung | webos | androidtv | firetv
"""


class SettingsError(ValueError):
    pass


def _explain(exc: ValidationError) -> str:
    """One short line per problem, in config.toml's own key names."""
    return "; ".join(
        f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
    )


def _parse_settings(path: Path) -> Settings:
    try:
        return Settings.model_validate(tomllib.loads(path.read_text()))
    except tomllib.TOMLDecodeError as exc:
        raise SettingsError(f"{path.name}: {exc}") from exc
    except ValidationError as exc:
        raise SettingsError(f"{path.name}: {_explain(exc)}") from exc


def _stamp(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    return st.st_mtime_ns, st.st_size


def _merge(doc: Any, values: dict[str, Any]) -> None:  # noqa: ANN401  # tomlkit containers
    for key, value in values.items():
        if isinstance(value, dict):
            if key not in doc:
                doc[key] = tomlkit.table()
            _merge(doc[key], value)  # pyright: ignore[reportUnknownArgumentType]
        elif value is None:
            doc.pop(key, None)
        elif key not in doc or doc[key] != value:
            doc[key] = value


def _write_atomic(path: Path, text: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    tmp.replace(path)


class SettingsFile:
    def __init__(self, config_dir: Path) -> None:
        self.path = config_dir / "config.toml"
        self.secrets_path = config_dir / "secrets.toml"
        if not self.path.exists():
            _write_atomic(self.path, TEMPLATE)
        self._settings = _parse_settings(self.path)  # boot: a broken file fails loudly
        self._secrets = self._read_secrets()
        self._stamps = (_stamp(self.path), _stamp(self.secrets_path))
        self.error: str | None = None

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def secrets(self) -> Secrets:
        return self._secrets

    @property
    def version(self) -> str:
        """Changes whenever either file changes on disk; the UI polls it to notice outside edits."""
        return ":".join(f"{s[0]}-{s[1]}" if s else "0" for s in self._stamps)

    def refresh(self) -> bool:
        """Re-read the files if they changed on disk. True if the running settings changed."""
        stamps = (_stamp(self.path), _stamp(self.secrets_path))
        if stamps == self._stamps:
            return False
        self._stamps = stamps
        before = (self._settings, self._secrets)
        try:
            self._settings = _parse_settings(self.path)
            self._secrets = self._read_secrets()
            self.error = None
        except SettingsError as exc:
            self.error = str(exc)
        return before != (self._settings, self._secrets)

    def save(self, values: dict[str, Any]) -> Settings:
        """Apply a partial update to the file as it is on disk now (only the given keys change, so
        a concurrent hand edit elsewhere survives), and write it only if the whole file is valid."""
        self.refresh()
        doc = _parse_doc(self.path)
        _merge(doc, _plain(values))
        try:
            settings = Settings.model_validate(doc.unwrap())
        except ValidationError as exc:
            raise SettingsError(_explain(exc)) from exc
        _write_atomic(self.path, tomlkit.dumps(doc))
        self._settings, self.error = settings, None
        self._stamps = (_stamp(self.path), self._stamps[1])
        return settings

    def set_secret(self, name: str, value: str | None) -> None:
        if name not in Secrets.model_fields:
            raise SettingsError(f"unknown secret {name!r}")
        doc = _parse_doc(self.secrets_path) if self.secrets_path.exists() else tomlkit.document()
        _merge(doc, {name: value or None})
        _write_atomic(self.secrets_path, tomlkit.dumps(doc), mode=0o600)
        self.secrets_path.chmod(0o600)
        self._secrets = self._read_secrets()
        self._stamps = (self._stamps[0], _stamp(self.secrets_path))

    def _read_secrets(self) -> Secrets:
        if not self.secrets_path.exists():
            return Secrets()
        # Errors name keys and lines only, and aren't chained: a traceback would print the values.
        name = self.secrets_path.name
        try:
            return Secrets.model_validate(tomllib.loads(self.secrets_path.read_text()))
        except tomllib.TOMLDecodeError as exc:  # line and column only, never the text
            raise SettingsError(f"{name}: invalid TOML at line {exc.lineno}") from None
        except ValidationError as exc:  # key names only: the values are secrets
            keys = ", ".join(".".join(str(p) for p in e["loc"]) for e in exc.errors())
            raise SettingsError(f"{name}: invalid or unknown key(s): {keys}") from None


def _plain(values: dict[str, Any]) -> dict[str, Any]:
    """TOML has strings, not IP objects."""
    out: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, dict):
            out[key] = _plain(cast(dict[str, Any], value))
        else:
            out[key] = str(value) if isinstance(value, IPv4Address) else value
    return out


def _parse_doc(path: Path) -> tomlkit.TOMLDocument:
    try:
        return tomlkit.parse(path.read_text())
    except TOMLKitError as exc:
        raise SettingsError(f"{path.name}: {exc}") from exc
