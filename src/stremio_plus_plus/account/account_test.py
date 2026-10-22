import json
import stat
from pathlib import Path
from typing import Any

import httpx
import pytest

from stremio_plus_plus.account.api import StremioApi, StremioApiError
from stremio_plus_plus.account.collection import addon_id, descriptor, ours_first
from stremio_plus_plus.account.credentials import AuthFile
from stremio_plus_plus.account.service import StremioAccount

OURS = "io.github.fum4.stremio-plus-plus"
URL = "https://192-168-1-132.519b6502d940.stremio.rocks:8443/tok/manifest.json"


def _addon(id_: str, url: str = "https://x/manifest.json") -> dict[str, Any]:
    return {"transportUrl": url, "manifest": {"id": id_, "name": id_}, "flags": {"official": True}}


class FakeStremio:
    def __init__(self, addons: list[dict[str, Any]]) -> None:
        self.addons = addons
        self.sets = 0
        self.keys = {"good-key"}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        method = request.url.path.rsplit("/", 1)[-1]
        if method == "login":
            if body["password"] != "pw":
                return httpx.Response(
                    200, json={"error": {"code": 3, "message": "Wrong passphrase"}}
                )
            return httpx.Response(200, json={"result": {"authKey": "good-key"}})
        if body.get("authKey") not in self.keys:
            return httpx.Response(
                200, json={"error": {"code": 1, "message": "Session does not exist"}}
            )
        if method == "getUser":
            return httpx.Response(200, json={"result": {"email": "me@example.com"}})
        if method == "addonCollectionGet":
            return httpx.Response(200, json={"result": {"addons": self.addons}})
        if method == "addonCollectionSet":
            self.addons, self.sets = body["addons"], self.sets + 1
            return httpx.Response(200, json={"result": {"success": True}})
        return httpx.Response(404)


def _account(tmp_path: Path, fake: FakeStremio, url: str | None = URL) -> StremioAccount:
    api = StremioApi(httpx.AsyncClient(transport=httpx.MockTransport(fake)), "https://api.test")
    return StremioAccount(
        api, AuthFile(tmp_path), OURS, {"id": OURS, "name": "Stremio++"}, lambda: url, lambda: True
    )


def test_ours_first_keeps_every_other_addon_in_order() -> None:
    addons = [_addon("cinemeta"), _addon("torrentio"), _addon(OURS), _addon(OURS)]
    assert [addon_id(a) for a in ours_first(addons, OURS)] == [OURS, "cinemeta", "torrentio"]
    fresh = ours_first(addons[:2], OURS, descriptor(URL, {"id": OURS}))
    assert [addon_id(a) for a in fresh] == [OURS, "cinemeta", "torrentio"]
    assert fresh[1] is addons[0]  # untouched objects, flags and all


def test_the_key_file_is_private_and_holds_only_the_key(tmp_path: Path) -> None:
    auth = AuthFile(tmp_path)
    auth.save("good-key")
    assert json.loads(auth.path.read_text()) == {"authKey": "good-key"}
    assert stat.S_IMODE(auth.path.stat().st_mode) == 0o600
    auth.clear()
    assert auth.load() is None


@pytest.mark.asyncio
async def test_login_stores_the_key_never_the_password(tmp_path: Path) -> None:
    fake = FakeStremio([_addon("cinemeta")])
    account = _account(tmp_path, fake)
    with pytest.raises(StremioApiError, match="Wrong passphrase"):
        await account.login("me@example.com", "nope")
    state = await account.login("me@example.com", "pw")
    assert state.connected and state.email == "me@example.com" and state.position is None
    assert "pw" not in (tmp_path / "stremio-auth.json").read_text()


@pytest.mark.asyncio
async def test_a_bad_pasted_key_is_not_stored(tmp_path: Path) -> None:
    account = _account(tmp_path, FakeStremio([]))
    with pytest.raises(StremioApiError):
        await account.use_key("stale-key")
    assert account.key is None
    assert (await account.use_key(' "good-key" ')).connected


@pytest.mark.asyncio
async def test_install_then_keep_it_first_and_on_the_current_url(tmp_path: Path) -> None:
    fake = FakeStremio([_addon("cinemeta"), _addon("torrentio")])
    account = _account(tmp_path, fake)
    await account.use_key("good-key")
    state = await account.install()
    assert (state.position, state.url_current) == (0, True)
    # Another addon installed in front of ours, and the host's URL changed meanwhile.
    fake.addons = [_addon("newcomer"), *fake.addons]
    fake.addons[1]["transportUrl"] = "https://stremio.nomadware.io:8443/tok/manifest.json"
    assert await account.keep()
    assert addon_id(fake.addons[0]) == OURS and fake.addons[0]["transportUrl"] == URL
    assert not await account.keep()  # nothing to do now


@pytest.mark.asyncio
async def test_keep_never_installs_by_itself(tmp_path: Path) -> None:
    fake = FakeStremio([_addon("cinemeta")])
    account = _account(tmp_path, fake)
    await account.use_key("good-key")
    assert not await account.keep() and fake.sets == 0


@pytest.mark.asyncio
async def test_a_revoked_session_says_so(tmp_path: Path) -> None:
    fake = FakeStremio([])
    account = _account(tmp_path, fake)
    await account.use_key("good-key")
    fake.keys.clear()
    state = await account.state(fresh=True)
    assert not state.connected and state.error and "connect again" in state.error


@pytest.mark.asyncio
async def test_a_bogus_addon_list_never_becomes_a_write(tmp_path: Path) -> None:
    fake = FakeStremio([_addon("cinemeta")])
    account = _account(tmp_path, fake)
    await account.use_key("good-key")
    for bogus in (None, {"x": 1}, ["not-a-dict"]):
        fake.addons = bogus  # type: ignore[assignment]
        with pytest.raises(StremioApiError):
            await account.install()
    fake.addons = []
    with pytest.raises(StremioApiError, match="nothing was changed"):
        await account.install()
    assert fake.sets == 0


@pytest.mark.asyncio
async def test_odd_replies_are_api_errors_without_the_request_attached(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": None} if "login" in str(request.url) else [1])

    api = StremioApi(httpx.AsyncClient(transport=httpx.MockTransport(handler)), "https://api.test")
    for call in (api.login("me@example.com", "pw-secret"), api.addons("k")):
        with pytest.raises(StremioApiError) as info:
            await call
        assert info.value.__cause__ is None and info.value.__suppress_context__


@pytest.mark.asyncio
async def test_move_to_top_works_with_keep_first_off(tmp_path: Path) -> None:
    fake = FakeStremio([_addon("cinemeta"), _addon(OURS, URL)])
    api = StremioApi(httpx.AsyncClient(transport=httpx.MockTransport(fake)), "https://api.test")
    account = StremioAccount(
        api, AuthFile(tmp_path), OURS, {"id": OURS}, lambda: URL, lambda: False
    )
    await account.use_key("good-key")
    assert not await account.keep()
    assert await account.keep(force=True) and addon_id(fake.addons[0]) == OURS


@pytest.mark.asyncio
async def test_an_outage_is_not_a_sign_out(tmp_path: Path) -> None:
    fake = FakeStremio([])
    account = _account(tmp_path, fake)
    await account.use_key("good-key")
    account._api = StremioApi(  # type: ignore[attr-defined]  # Stremio unreachable
        httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(502, text="x"))),
        "https://api.test",
    )
    state = await account.state(fresh=True)
    assert state.connected and state.error and "unreachable" in state.error


@pytest.mark.asyncio
async def test_collection_for_readers_is_none_without_an_account_or_on_errors(
    tmp_path: Path,
) -> None:
    fake = FakeStremio([_addon("torrentio")])
    account = _account(tmp_path, fake)
    assert await account.collection() is None
    await account.use_key("good-key")
    collection = await account.collection()
    assert collection is not None and addon_id(collection[0]) == "torrentio"
    fake.keys.clear()
    assert await account.collection() is None
