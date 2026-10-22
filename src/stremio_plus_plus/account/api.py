"""The Stremio account API (api.strem.io): login, the user, and the addon collection.

Every call is POST /api/<method> with a typed body; replies are {"result": …} or
{"error": {"code", "message"}}. Code 1 = the session (authKey) no longer exists.
"""

from typing import Any, cast

import httpx

API = "https://api.strem.io/api"
TIMEOUT_S = 15.0
SESSION_GONE = 1


class StremioApiError(RuntimeError):
    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code

    @property
    def session_gone(self) -> bool:
        return self.code == SESSION_GONE


class StremioApi:
    def __init__(self, http: httpx.AsyncClient, base: str = API) -> None:
        self._http = http
        self._base = base

    async def _call(self, method: str, body: dict[str, Any]) -> dict[str, Any]:
        """The `result` object. Any failure becomes a StremioApiError raised `from None`: the
        request body (password, authKey) must never reach a traceback, and tracebacks get logged."""
        try:
            resp = await self._http.post(f"{self._base}/{method}", json=body, timeout=TIMEOUT_S)
            data: object = resp.json()
        except Exception as exc:
            raise StremioApiError(f"Stremio's API is unreachable ({type(exc).__name__})") from None
        if not isinstance(data, dict):
            raise StremioApiError("Stremio's API sent an unexpected reply") from None
        reply = cast(dict[str, Any], data)
        if isinstance(error := reply.get("error"), dict):
            err = cast(dict[str, Any], error)
            code = err.get("code")
            raise StremioApiError(
                str(err.get("message", "error")), code if isinstance(code, int) else None
            ) from None
        result = reply.get("result")
        if not isinstance(result, dict):
            raise StremioApiError("Stremio's API sent an unexpected reply") from None
        return cast(dict[str, Any], result)

    async def login(self, email: str, password: str) -> str:
        """The authKey for an email/password account. The password goes nowhere else."""
        body = {"type": "Login", "email": email, "password": password, "facebook": False}
        key = (await self._call("login", body)).get("authKey")
        if not isinstance(key, str) or not key:
            raise StremioApiError("Stremio's API sent no login key") from None
        return key

    async def email(self, auth_key: str) -> str | None:
        result = await self._call("getUser", {"type": "GetUser", "authKey": auth_key})
        email = result.get("email")
        return email if isinstance(email, str) else None

    async def addons(self, auth_key: str) -> list[dict[str, Any]]:
        """The collection, validated: a reply that isn't a list of addons is an error, never []
        (writing back a list built on a bogus empty one would wipe the user's addons)."""
        body = {"type": "AddonCollectionGet", "authKey": auth_key, "update": True}
        addons = (await self._call("addonCollectionGet", body)).get("addons")
        if not isinstance(addons, list) or not all(isinstance(a, dict) for a in addons):  # pyright: ignore[reportUnknownVariableType]
            raise StremioApiError("Stremio's API sent an unexpected addon list") from None
        return cast(list[dict[str, Any]], addons)

    async def set_addons(self, auth_key: str, addons: list[dict[str, Any]]) -> None:
        body = {"type": "AddonCollectionSet", "authKey": auth_key, "addons": addons}
        if not (await self._call("addonCollectionSet", body)).get("success"):
            raise StremioApiError("Stremio didn't accept the addon list") from None
