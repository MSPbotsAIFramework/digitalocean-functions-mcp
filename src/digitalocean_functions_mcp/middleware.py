"""Per-request credential handling.

The gateway serves multiple tenants concurrently through one running
container; each request carries its own DigitalOcean token in
`X-Digitalocean-Token`. The token is never read from the environment,
never stored on a global/module-level object, and lives only in a
`contextvars.ContextVar` that is reset in `finally` -- this is the entire
multi-tenant isolation mechanism (no other request-scoped or cross-request
state exists in this service).
"""

import contextlib
import contextvars
import json

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

CREDENTIAL_HEADER = "X-Digitalocean-Token"

_token_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("do_token", default=None)


def current_token() -> str | None:
    """Read the DigitalOcean token for the in-flight request, if any."""
    return _token_ctx.get()


@contextlib.contextmanager
def credential_context(token: str | None):
    """Set the per-request token outside of an actual ASGI request.

    Used by tests to exercise tool functions directly (the same
    set/reset-in-finally mechanism the ASGI middleware itself uses, so a
    test simulates exactly the isolation guarantee it is checking)."""
    reset_token = _token_ctx.set(token)
    try:
        yield
    finally:
        _token_ctx.reset(reset_token)


def _missing_header_response() -> Response:
    body = json.dumps(
        {
            "error": {
                "code": "unauthorized",
                "message": f"Missing required header: {CREDENTIAL_HEADER}",
                "retryable": False,
            },
            "required_headers": [CREDENTIAL_HEADER],
        },
        separators=(",", ":"),
    )
    return Response(content=body, status_code=401, media_type="application/json")


class CredentialMiddleware:
    """ASGI middleware: reads the credential header for `/mcp` requests only,
    sets the per-request ContextVar, and always resets it afterward.

    `/health` is intentionally untouched -- it must stay a pure local
    liveness probe independent of credentials or upstream reachability.
    """

    def __init__(self, app: ASGIApp, mount_path: str = "/mcp"):
        self.app = app
        self.mount_path = mount_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(self.mount_path):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        token = request.headers.get(CREDENTIAL_HEADER)
        if not token:
            response = _missing_header_response()
            await response(scope, receive, send)
            return

        reset_token = _token_ctx.set(token)
        try:
            await self.app(scope, receive, send)
        finally:
            _token_ctx.reset(reset_token)
