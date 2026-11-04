"""Tools for namespace access keys on a DigitalOcean Functions namespace.

Maps 1:1 onto:
  GET    /v2/functions/namespaces/{namespace_id}/access-keys
  POST   /v2/functions/namespaces/{namespace_id}/access-keys
  PUT    /v2/functions/namespaces/{namespace_id}/access-keys/{key_id}
  DELETE /v2/functions/namespaces/{namespace_id}/access-keys/{key_id}

The one-time key value DigitalOcean returns from create is passed back to
the caller (the agent needs it to use the key) but is never written to our
own log lines (AC11) -- the client/error layers only ever log resource ids,
never response bodies, so this holds structurally rather than needing a
redaction step here.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..errors import ToolError, from_tool_error
from ..serialization import dumps


def register(mcp: FastMCP, client_factory) -> dict:
    @mcp.tool(
        description="List the namespace access keys for a DigitalOcean Functions namespace.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def digitalocean_list_access_keys(namespace_id: str) -> str:
        if not namespace_id:
            return from_tool_error(ToolError("invalid_argument", "namespace_id is required"))
        client = client_factory()
        try:
            payload = await client.get(f"/v2/functions/namespaces/{namespace_id}/access-keys")
        except ToolError as err:
            return from_tool_error(err)
        keys = (payload or {}).get("keys", [])
        return dumps({"keys": keys})

    @mcp.tool(
        description="Create a namespace access key for a DigitalOcean Functions namespace. Requires a name.",
    )
    async def digitalocean_create_access_key(
        namespace_id: str,
        name: str | None = None,
        expires_at: str | None = None,
    ) -> str:
        if not namespace_id:
            return from_tool_error(ToolError("invalid_argument", "namespace_id is required"))
        if not name:
            return from_tool_error(ToolError("invalid_argument", "name is required"))
        body: dict[str, Any] = {"name": name}
        if expires_at is not None:
            body["expires_at"] = expires_at
        client = client_factory()
        try:
            payload = await client.post(f"/v2/functions/namespaces/{namespace_id}/access-keys", body)
        except ToolError as err:
            return from_tool_error(err)
        key = (payload or {}).get("key", payload)
        return dumps(key)

    @mcp.tool(
        description="Update a namespace access key by id.",
    )
    async def digitalocean_update_access_key(
        namespace_id: str,
        key_id: str,
        name: str | None = None,
        expires_at: str | None = None,
    ) -> str:
        if not namespace_id or not key_id:
            return from_tool_error(ToolError("invalid_argument", "namespace_id and key_id are required"))
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if expires_at is not None:
            body["expires_at"] = expires_at
        if not body:
            return from_tool_error(ToolError("invalid_argument", "at least one updatable field is required"))
        client = client_factory()
        try:
            payload = await client.put(f"/v2/functions/namespaces/{namespace_id}/access-keys/{key_id}", body)
        except ToolError as err:
            return from_tool_error(err)
        key = (payload or {}).get("key", payload)
        return dumps(key)

    @mcp.tool(
        description="Delete a namespace access key by id. Requires an explicit key_id; there is no wildcard delete.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    async def digitalocean_delete_access_key(namespace_id: str, key_id: str | None = None) -> str:
        if not namespace_id or not key_id:
            return from_tool_error(ToolError("invalid_argument", "namespace_id and key_id are required"))
        client = client_factory()
        try:
            await client.delete(f"/v2/functions/namespaces/{namespace_id}/access-keys/{key_id}")
        except ToolError as err:
            return from_tool_error(err)
        return dumps({"deleted": True, "namespace_id": namespace_id, "key_id": key_id})

    return {
        "digitalocean_list_access_keys": digitalocean_list_access_keys,
        "digitalocean_create_access_key": digitalocean_create_access_key,
        "digitalocean_update_access_key": digitalocean_update_access_key,
        "digitalocean_delete_access_key": digitalocean_delete_access_key,
    }
