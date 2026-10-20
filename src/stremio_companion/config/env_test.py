import pytest
from pydantic import ValidationError

from stremio_companion.config.env import load_env

VALID = {
    "STREMIO_SERVER_URL": "http://127.0.0.1:11470",
    "COMPANION_HOST": "0.0.0.0",
    "COMPANION_PORT": "11471",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "json",
}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for key in VALID:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_loads_a_complete_environment(env: pytest.MonkeyPatch) -> None:
    for key, value in VALID.items():
        env.setenv(key, value)
    loaded = load_env()
    assert loaded.companion_port == 11471
    assert str(loaded.stremio_server_url) == "http://127.0.0.1:11470/"


@pytest.mark.parametrize("missing", sorted(VALID))
def test_fails_on_any_missing_value(env: pytest.MonkeyPatch, missing: str) -> None:
    for key, value in VALID.items():
        if key != missing:
            env.setenv(key, value)
    with pytest.raises(ValidationError):
        load_env()


@pytest.mark.parametrize(("key", "bad"), [("COMPANION_PORT", "0"), ("LOG_LEVEL", "LOUD")])
def test_fails_on_invalid_value(env: pytest.MonkeyPatch, key: str, bad: str) -> None:
    for k, value in VALID.items():
        env.setenv(k, value)
    env.setenv(key, bad)
    with pytest.raises(ValidationError):
        load_env()
