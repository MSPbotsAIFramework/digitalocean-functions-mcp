import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from digitalocean_functions_mcp import client as client_module
from digitalocean_functions_mcp.server import SERVICE_INSTRUCTIONS
from digitalocean_functions_mcp.tools import access_keys, namespaces, triggers

BASE_URL = "https://api.digitalocean.com"
TOKEN_A = "do_v1_tenant_a_token"
TOKEN_B = "do_v1_tenant_b_token"


@pytest.fixture(autouse=True)
async def _fresh_shared_client():
    """Each test gets its own httpx.AsyncClient bound to its own event loop
    (pytest-asyncio creates a new loop per test by default); an
    httpx.AsyncClient from a previous test's loop would raise on reuse."""
    await client_module.reset_shared_client()
    yield
    await client_module.reset_shared_client()


@pytest.fixture
def mcp():
    """Same wiring as server.build_fastmcp(), built directly here so the
    `tools` fixture below can capture the raw (undecorated) tool functions
    the register() calls return, instead of reaching into FastMCP internals."""
    return FastMCP(
        name="digitalocean-functions-mcp",
        instructions=SERVICE_INSTRUCTIONS,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


@pytest.fixture
def tools(mcp):
    client_factory = client_module.client_factory(BASE_URL)
    merged: dict = {}
    merged.update(namespaces.register(mcp, client_factory))
    merged.update(triggers.register(mcp, client_factory))
    merged.update(access_keys.register(mcp, client_factory))
    return merged
