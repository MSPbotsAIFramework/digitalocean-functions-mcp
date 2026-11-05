"""Tools for DigitalOcean Functions namespaces.

Maps 1:1 onto:
  GET    /v2/functions/namespaces
  POST   /v2/functions/namespaces
  GET    /v2/functions/namespaces/{namespace_id}
  DELETE /v2/functions/namespaces/{namespace_id}
"""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..errors import ToolError, from_tool_error
from ..serialization import dumps


def register(mcp: FastMCP, client_factory) -> dict:
    """Register namespace tools on `mcp`. Returns the raw async functions
    (unwrapped by the decorator) keyed by tool name, so tests can call them
    directly without going through the MCP protocol envelope."""

    @mcp.tool(
        description="List the DigitalOcean Functions namespaces visible to the caller's token.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def digitalocean_list_namespaces() -> str:
        client = client_factory()
        try:
            payload = await client.get("/v2/functions/namespaces")
        except ToolError as err:
            return from_tool_error(err)
        namespaces = (payload or {}).get("namespaces", [])
        return dumps({"namespaces": namespaces})

    @mcp.tool(
        description="Create a DigitalOcean Functions namespace. Requires label and region.",
    )
    async def digitalocean_create_namespace(label: str, region: str | None = None) -> str:
        if not region:
            return from_tool_error(ToolError("invalid_argument", "region is required"))
        if not label:
            return from_tool_error(ToolError("invalid_argument", "label is required"))
        client = client_factory()
        try:
            payload = await client.post("/v2/functions/namespaces", {"label": label, "region": region})
        except ToolError as err:
            return from_tool_error(err)
        namespace = (payload or {}).get("namespace", payload)
        return dumps(namespace)

    @mcp.tool(
        description="Get the details of a single DigitalOcean Functions namespace by id.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def digitalocean_get_namespace(namespace_id: str) -> str:
        if not namespace_id:
            return from_tool_error(ToolError("invalid_argument", "namespace_id is required"))
        client = client_factory()
        try:
            payload = await client.get(f"/v2/functions/namespaces/{namespace_id}")
        except ToolError as err:
            return from_tool_error(err)
        namespace = (payload or {}).get("namespace", payload)
        return dumps(namespace)

    @mcp.tool(
        description="Delete a DigitalOcean Functions namespace and everything in it. Requires an explicit namespace_id; there is no delete-all form.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    async def digitalocean_delete_namespace(namespace_id: str | None = None) -> str:
        if not namespace_id:
            return from_tool_error(ToolError("invalid_argument", "namespace_id is required"))
        client = client_factory()
        try:
            await client.delete(f"/v2/functions/namespaces/{namespace_id}")
        except ToolError as err:
            return from_tool_error(err)
        return dumps({"deleted": True, "namespace_id": namespace_id})

    return {
        "digitalocean_list_namespaces": digitalocean_list_namespaces,
        "digitalocean_create_namespace": digitalocean_create_namespace,
        "digitalocean_get_namespace": digitalocean_get_namespace,
        "digitalocean_delete_namespace": digitalocean_delete_namespace,
    }
