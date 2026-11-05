"""FastMCP app factory.

Wires together: the stateless FastMCP server, the per-request credential
middleware, the DigitalOcean client factory, and a local `/health` probe
that is intentionally independent of DigitalOcean's reachability.
"""

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .client import client_factory as make_client_factory
from .middleware import CredentialMiddleware
from .tools import access_keys, namespaces, triggers

SERVICE_INSTRUCTIONS = (
    "Manage DigitalOcean Functions: serverless namespaces, their triggers, "
    "and their namespace access keys. Typical flow: list or create a "
    "namespace, then create triggers inside it to invoke functions on a "
    "schedule or event, and namespace access keys to grant programmatic "
    "access to that namespace. Deploying or invoking the function code "
    "itself is out of scope for this connector -- it manages the "
    "namespace/trigger/access-key resources, not function code."
)


async def health(_request: Request) -> JSONResponse:
    # Pure local liveness probe: must stay 200 even if DigitalOcean is down
    # or the caller's token is missing/invalid (SOP S1.1).
    return JSONResponse({"status": "ok"})


def build_fastmcp(base_url: str) -> FastMCP:
    mcp = FastMCP(
        name="digitalocean-functions-mcp",
        instructions=SERVICE_INSTRUCTIONS,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    client_factory = make_client_factory(base_url)
    namespaces.register(mcp, client_factory)
    triggers.register(mcp, client_factory)
    access_keys.register(mcp, client_factory)
    return mcp


def build_app(base_url: str):
    """Build the outer ASGI app: `/health` (local probe) + `/mcp` (MCP,
    guarded by CredentialMiddleware), with the FastMCP session manager's
    lifespan explicitly wired to the outer app -- `Mount()` alone does not
    run a mounted sub-app's lifespan (SOP S7), and skipping this makes
    `/mcp` fail with "Task group is not initialized" while `/health` still
    reports 200.
    """
    mcp = build_fastmcp(base_url)
    mcp_app = mcp.streamable_http_app()

    inner = Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Mount("/", app=mcp_app),
        ],
        lifespan=mcp_app.router.lifespan_context,
    )
    return CredentialMiddleware(inner, mount_path="/mcp")
