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

    async def _call(self, method: str, body: dict[str, Any]) -> Any:  # noqa: ANN401  # JSON
        try:
            resp = await self._http.post(f"{self._base}/{method}", json=body, timeout=TIMEOUT_S)
            data = cast(dict[str, Any], resp.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise StremioApiError(f"Stremio's API is unreachable ({type(exc).__name__})") from exc
        if error := data.get("error"):
            err = cast(dict[str, Any], error)
            raise StremioApiError(str(err.get("message", "error")), err.get("code"))
        return data.get("result")

    async def login(self, email: str, password: str) -> str:
        """The authKey for an email/password account. The password goes nowhere else."""
        body = {"type": "Login", "email": email, "password": password, "facebook": False}
        result = cast(dict[str, Any], await self._call("login", body))
        return str(result["authKey"])

    async def email(self, auth_key: str) -> str | None:
        result = cast(
            dict[str, Any], await self._call("getUser", {"type": "GetUser", "authKey": auth_key})
        )
        return cast(str | None, result.get("email"))

    async def addons(self, auth_key: str) -> list[dict[str, Any]]:
        body = {"type": "AddonCollectionGet", "authKey": auth_key, "update": True}
        result = cast(dict[str, Any], await self._call("addonCollectionGet", body))
        return cast(list[dict[str, Any]], result.get("addons") or [])

    async def set_addons(self, auth_key: str, addons: list[dict[str, Any]]) -> None:
        body = {"type": "AddonCollectionSet", "authKey": auth_key, "addons": addons}
        result = cast(dict[str, Any], await self._call("addonCollectionSet", body))
        if not result.get("success"):
            raise StremioApiError("Stremio didn't accept the addon list")
