"""Thin async HTTP client for the DigitalOcean Functions REST API.

One `httpx.AsyncClient` is created at process start and reused for every
request (connection pooling only -- no per-tenant data is ever cached on
it). The caller's token is read from the per-request ContextVar
(middleware.py) and turned into `Authorization: Bearer <token>` on each
individual call; the client itself holds no credential state.
"""

import asyncio
import logging
import random
import time

import httpx

from .errors import ToolError, map_status_code
from .middleware import current_token

logger = logging.getLogger("digitalocean_functions_mcp")

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0
MAX_RETRIES = 4
MAX_TOTAL_SECONDS = 110.0  # stays under the 120s SOP budget including the initial attempt

_client: httpx.AsyncClient | None = None


def get_shared_client(base_url: str) -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT, write=READ_TIMEOUT, pool=READ_TIMEOUT),
        )
    return _client


async def reset_shared_client() -> None:
    """Test-only: drop the cached client so a fresh one picks up a new base_url/transport."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _auth_headers() -> dict[str, str]:
    token = current_token()
    if not token:
        # Middleware already rejects requests with no header before any tool
        # runs; this only guards direct unit-test calls into the client.
        raise ToolError("not_configured", "No DigitalOcean token in the current request context")
    return {"Authorization": f"Bearer {token}"}


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


class DigitalOceanClient:
    """Resource-agnostic REST helper: one method per HTTP verb, shared by
    every tool module. Retries 429/5xx with bounded backoff; all other
    failures are mapped once and raised as ToolError."""

    def __init__(self, base_url: str):
        self._base_url = base_url

    async def request(self, method: str, path: str, *, json_body: dict | None = None) -> dict | None:
        """Public entry point: times the call and logs exactly one summary
        line per tool call -- method, path (resource ids only, no query
        string with secrets), outcome, elapsed time. Never logs headers,
        request/response bodies, or the Authorization header, so response
        payloads (including one-time values like a created access key) never
        reach the logs (SOP S6 / AC11)."""
        start = time.monotonic()
        try:
            result = await self._request_with_retries(method, path, json_body=json_body)
        except ToolError as err:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.info("method=%s path=%s outcome=error code=%s elapsed_ms=%d", method, path, err.code, elapsed_ms)
            raise
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info("method=%s path=%s outcome=ok elapsed_ms=%d", method, path, elapsed_ms)
        return result

    async def _request_with_retries(self, method: str, path: str, *, json_body: dict | None = None) -> dict | None:
        client = get_shared_client(self._base_url)
        headers = _auth_headers()
        elapsed = 0.0
        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            if elapsed >= MAX_TOTAL_SECONDS:
                break
            try:
                response = await client.request(method, path, json=json_body, headers=headers)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt == MAX_RETRIES:
                    raise ToolError("upstream_error", f"Network error calling DigitalOcean: {exc}") from exc
                delay = min(_backoff_delay(attempt), max(0.0, MAX_TOTAL_SECONDS - elapsed))
                elapsed += delay
                await asyncio.sleep(delay)
                continue

            if response.status_code in (429, 500, 502, 503, 504):
                if attempt == MAX_RETRIES:
                    raise map_status_code(response.status_code, _safe_message(response))
                delay = _retry_after_seconds(response)
                if delay is None:
                    delay = _backoff_delay(attempt)
                # PRD-21342 round 1: DigitalOcean's Retry-After is untrusted input --
                # clamp it to what is left of the 120s SOP budget so one large value
                # can't hold a tool call open past the cap (AC16 / SOP 5).
                delay = min(delay, max(0.0, MAX_TOTAL_SECONDS - elapsed))
                elapsed += delay
                await asyncio.sleep(delay)
                continue

            if response.status_code >= 400:
                raise map_status_code(response.status_code, _safe_message(response))

            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        if last_exc is not None:
            raise ToolError("upstream_error", f"Network error calling DigitalOcean: {last_exc}")
        raise ToolError("upstream_error", "DigitalOcean did not respond within the retry budget")

    async def get(self, path: str) -> dict | None:
        return await self.request("GET", path)

    async def post(self, path: str, json_body: dict) -> dict | None:
        return await self.request("POST", path, json_body=json_body)

    async def put(self, path: str, json_body: dict) -> dict | None:
        return await self.request("PUT", path, json_body=json_body)

    async def delete(self, path: str) -> dict | None:
        return await self.request("DELETE", path)


def _backoff_delay(attempt: int) -> float:
    base = min(1.0 * (2**attempt), 8.0)
    return base + random.uniform(0, 0.25)


def _safe_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            msg = payload.get("message") or payload.get("error")
            if msg:
                return str(msg)
    except ValueError:
        pass
    return f"DigitalOcean returned HTTP {response.status_code}"


def client_factory(base_url: str):
    def _make() -> DigitalOceanClient:
        return DigitalOceanClient(base_url)

    return _make
