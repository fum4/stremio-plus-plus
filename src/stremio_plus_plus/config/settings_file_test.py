import os
import stat
from pathlib import Path

import pytest

from stremio_plus_plus.config.settings import Settings
from stremio_plus_plus.config.settings_file import SettingsError, SettingsFile


def _touch_later(path: Path) -> None:
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))


def test_first_run_writes_the_commented_template_with_the_defaults(tmp_path: Path) -> None:
    f = SettingsFile(tmp_path)
    assert f.settings == Settings()
    assert "# stremio++ settings" in f.path.read_text()


def test_save_keeps_comments_and_validates(tmp_path: Path) -> None:
    f = SettingsFile(tmp_path)
    f.save({"subtitles": {"translator": {"provider": "anthropic", "model": "claude-sonnet-5-5"}}})
    text = f.path.read_text()
    assert 'provider = "anthropic"' in text and "# claude-cli (your Claude" in text
    assert SettingsFile(tmp_path).settings.subtitles.translator.model == "claude-sonnet-5-5"
    with pytest.raises(SettingsError):
        f.save({"downloads": {"min_free_gb": -1}})


def test_outside_edits_reload_and_broken_ones_keep_the_last_good(tmp_path: Path) -> None:
    f = SettingsFile(tmp_path)
    f.path.write_text(f.path.read_text().replace("min_free_gb = 3", "min_free_gb = 9"))
    _touch_later(f.path)
    assert f.refresh() and f.settings.downloads.min_free_gb == 9
    f.path.write_text("[downloads]\nmin_free_gb = 'lots'\n")
    _touch_later(f.path)
    assert not f.refresh()
    assert f.settings.downloads.min_free_gb == 9
    assert f.error and f.error.startswith("config.toml: downloads.min_free_gb: Input should be")


def test_save_only_touches_given_keys_and_refuses_to_keep_a_broken_file(tmp_path: Path) -> None:
    f = SettingsFile(tmp_path)
    # A hand edit the companion hasn't polled yet must survive a UI save of another key.
    f.path.write_text(f.path.read_text().replace("stale_after_days = 7", "stale_after_days = 30"))
    f.save({"downloads": {"min_free_gb": 5}})
    assert (f.settings.downloads.min_free_gb, f.settings.downloads.stale_after_days) == (5, 30)
    # A typo'd key on disk: saving can't make the file valid, so it refuses instead of hiding it.
    f.path.write_text(f.path.read_text() + "\nmin_free_bg = 3\n")
    with pytest.raises(SettingsError, match="min_free_bg"):
        f.save({"downloads": {"min_free_gb": 6}})
    f.path.write_text("[downloads\n")
    with pytest.raises(SettingsError):
        f.save({"downloads": {"min_free_gb": 6}})


def test_unknown_keys_are_errors_not_silent(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text("[downloads]\nmin_free_bg = 3\n")
    with pytest.raises(SettingsError):
        SettingsFile(tmp_path)


def test_secrets_are_private_and_clearable(tmp_path: Path) -> None:
    f = SettingsFile(tmp_path)
    f.set_secret("anthropic_api_key", "sk-ant-test")
    assert f.secrets.anthropic_api_key == "sk-ant-test"
    assert stat.S_IMODE(f.secrets_path.stat().st_mode) == 0o600
    f.set_secret("anthropic_api_key", None)
    assert f.secrets.anthropic_api_key is None
    with pytest.raises(SettingsError):
        f.set_secret("nope", "x")


def test_a_broken_secrets_file_never_echoes_the_secret(tmp_path: Path) -> None:
    f = SettingsFile(tmp_path)
    f.secrets_path.write_text('anthropic_api_kye = "sk-ant-very-secret"\n')
    _touch_later(f.secrets_path)
    f.refresh()
    assert f.error == "secrets.toml: invalid or unknown key(s): anthropic_api_kye"
