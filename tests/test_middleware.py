import json

import httpx
import pytest
import respx

from digitalocean_functions_mcp.middleware import CREDENTIAL_HEADER, credential_context, current_token
from digitalocean_functions_mcp.server import build_app

from conftest import BASE_URL, TOKEN_A, TOKEN_B


@pytest.fixture
def app():
    return build_app(BASE_URL)


async def _client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_missing_credential_header_is_401_with_header_name(app):
    async with await _client(app) as client:
        resp = await client.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "unauthorized"
    assert CREDENTIAL_HEADER in body["required_headers"]
    assert CREDENTIAL_HEADER in body["error"]["message"]


async def test_health_independent_of_upstream_reachability(app, respx_mock):
    # DigitalOcean unreachable: any call to it would time out/connection-error.
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces").mock(side_effect=httpx.ConnectError("unreachable"))
    async with await _client(app) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    # Same with a credential header present -- /health still ignores it.
    async with await _client(app) as client:
        resp = await client.get("/health", headers={CREDENTIAL_HEADER: "whatever"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@respx.mock
async def test_credential_context_isolated_across_requests(tools):
    route = respx.get(f"{BASE_URL}/v2/functions/namespaces")
    route.side_effect = [
        httpx.Response(200, json={"namespaces": [{"namespace_id": "fn-a", "label": "tenant-a", "region": "nyc1"}]}),
        httpx.Response(200, json={"namespaces": [{"namespace_id": "fn-b", "label": "tenant-b", "region": "ams3"}]}),
    ]

    assert current_token() is None

    with credential_context(TOKEN_A):
        result_a = json.loads(await tools["digitalocean_list_namespaces"]())
    assert current_token() is None  # reset in finally, same as the real middleware

    with credential_context(TOKEN_B):
        result_b = json.loads(await tools["digitalocean_list_namespaces"]())
    assert current_token() is None

    assert result_a["namespaces"][0]["namespace_id"] == "fn-a"
    assert result_b["namespaces"][0]["namespace_id"] == "fn-b"
    assert result_a != result_b

    sent_auth_headers = [call.request.headers["Authorization"] for call in route.calls]
    assert sent_auth_headers == [f"Bearer {TOKEN_A}", f"Bearer {TOKEN_B}"]
