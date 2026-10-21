"""On the public HTTPS listener, serve only the token-prefixed addon routes; everything else
(health, SRT, unknown paths) is 404 there and stays LAN-only on the plain-http port."""

from starlette.types import ASGIApp, Receive, Scope, Send


class HttpsGuard:
    def __init__(self, app: ASGIApp, https_port: int, token: str) -> None:
        self._app = app
        self._https_port = https_port
        self._prefix = f"/{token}/"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        server = scope.get("server")
        on_https = scope["type"] == "http" and server is not None and server[1] == self._https_port
        if on_https and not str(scope["path"]).startswith(self._prefix):
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b""})
            return
        await self._app(scope, receive, send)
