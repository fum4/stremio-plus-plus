import time
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stremio_plus_plus.app import addon
from stremio_plus_plus.app.addon import addon_router, lan_router
from stremio_plus_plus.app.services_test_support import TOKEN, make_services
from stremio_plus_plus.server.constants import SUBTITLE_PROXY_TIMEOUT_S
from stremio_plus_plus.subtitles.cues import Cue
from stremio_plus_plus.subtitles.jobs import SubtitleJobs
from stremio_plus_plus.subtitles.store import SubtitleStore

IH = "ab" * 20
STATS = {
    IH: {
        "name": "MobLand S01",
        "files": [{"name": "Pack/MobLand.S01E03.mkv", "length": 3560556831}],
    }
}


def _client(tmp_path: Path) -> tuple[TestClient, SubtitleStore]:
    client, store, _ = _client_and_jobs(tmp_path)
    return client, store


def _client_and_jobs(tmp_path: Path) -> tuple[TestClient, SubtitleStore, SubtitleJobs]:
    services = make_services(tmp_path, lambda r: httpx.Response(200, json=STATS))
    app = FastAPI()
    app.include_router(addon_router)
    app.include_router(lan_router)
    app.state.services = services
    return TestClient(app), services.subtitle_store, services.subtitles


def test_manifest_names_the_addon_stremio_plus_plus(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.get(f"/{TOKEN}/manifest.json").json()["name"] == "Stremio++"


def test_subtitles_request_matches_the_playing_file_by_name(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    resp = client.get(
        f"/{TOKEN}/subtitles/series/tt31510819:1:3/filename=MobLand.S01E03.mkv&videoSize=3560556831&videoHash=1e89.json"
    )
    [track] = resp.json()["subtitles"]
    assert track["lang"] == "ron" and track["label"] == "Romanian (AI)"
    assert track["url"] == f"http://192.168.1.132:11471/srt/{IH}/0.srt"


def test_unknown_file_gets_no_track(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.get(f"/{TOKEN}/subtitles/movie/tt1/filename=Other.mkv.json").json() == {
        "subtitles": []
    }


def test_srt_serves_stored_cues_or_a_placeholder(tmp_path: Path) -> None:
    client, store = _client(tmp_path)
    assert "Se generează" in client.get(f"/srt/{IH}/0.srt").text
    store.save_span(IH, 0, (0.0, 15.0), [Cue(1.0, 2.0, "Unu")])
    assert client.get(f"/srt/{IH}/0.srt").text == "1\n00:00:01,000 --> 00:00:02,000\nUnu\n"


def test_srt_waits_a_bounded_time_for_a_file_being_generated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(addon, "FIRST_ANSWER_WAIT_S", 1.0)
    client, _, jobs = _client_and_jobs(tmp_path)
    jobs.ensure(IH, 0, "MobLand.S01E03.mkv", 3560556831)  # nothing generated yet
    t0 = time.monotonic()
    assert "Se generează" in client.get(f"/srt/{IH}/0.srt").text
    assert 1.0 <= time.monotonic() - t0 < 3.0


def test_wrong_token_is_404(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.get("/" + "z" * 32 + "/manifest.json").status_code == 404
    assert client.get("/manifest.json").status_code == 404


def test_the_first_answer_wait_stays_under_the_server_subtitle_proxy_timeout() -> None:
    # Longer, and the TV shows "failed to load external subtitles" instead of the placeholder.
    assert addon.FIRST_ANSWER_WAIT_S <= SUBTITLE_PROXY_TIMEOUT_S - 2.0
