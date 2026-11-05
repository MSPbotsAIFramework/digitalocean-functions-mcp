"""Tools for triggers on a DigitalOcean Functions namespace.

Maps 1:1 onto:
  GET    /v2/functions/namespaces/{namespace_id}/triggers
  POST   /v2/functions/namespaces/{namespace_id}/triggers
  GET    /v2/functions/namespaces/{namespace_id}/triggers/{trigger_name}
  PUT    /v2/functions/namespaces/{namespace_id}/triggers/{trigger_name}
  DELETE /v2/functions/namespaces/{namespace_id}/triggers/{trigger_name}
"""

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..errors import ToolError, from_tool_error
from ..serialization import dumps

# Open question in the design (assumed, not blocking): DigitalOcean's public
# reference for trigger bodies lists field names, not a full JSON schema.
# These three are treated as required to create a trigger; `scheduled_details`
# is accepted as an opaque dict so a richer real-world shape does not require
# a client-side schema change -- only this validation list would need review.
REQUIRED_CREATE_FIELDS = ("name", "function", "type")


def register(mcp: FastMCP, client_factory) -> dict:
    @mcp.tool(
        description="List the triggers configured on a DigitalOcean Functions namespace.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def digitalocean_list_triggers(namespace_id: str) -> str:
        if not namespace_id:
            return from_tool_error(ToolError("invalid_argument", "namespace_id is required"))
        client = client_factory()
        try:
            payload = await client.get(f"/v2/functions/namespaces/{namespace_id}/triggers")
        except ToolError as err:
            return from_tool_error(err)
        triggers = (payload or {}).get("triggers", [])
        return dumps({"triggers": triggers})

    @mcp.tool(
        description="Create a trigger on a DigitalOcean Functions namespace. Requires name, function, and type.",
    )
    async def digitalocean_create_trigger(
        namespace_id: str,
        name: str | None = None,
        function: str | None = None,
        type: str | None = None,
        is_enabled: bool = True,
        scheduled_details: dict[str, Any] | None = None,
    ) -> str:
        if not namespace_id:
            return from_tool_error(ToolError("invalid_argument", "namespace_id is required"))
        body = {"name": name, "function": function, "type": type}
        missing = [field for field in REQUIRED_CREATE_FIELDS if not body.get(field)]
        if missing:
            return from_tool_error(ToolError("invalid_argument", f"missing required field(s): {', '.join(missing)}"))
        body["is_enabled"] = is_enabled
        if scheduled_details is not None:
            body["scheduled_details"] = scheduled_details
        client = client_factory()
        try:
            payload = await client.post(f"/v2/functions/namespaces/{namespace_id}/triggers", body)
        except ToolError as err:
            return from_tool_error(err)
        trigger = (payload or {}).get("trigger", payload)
        return dumps(trigger)

    @mcp.tool(
        description="Get the details of a single trigger by name.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def digitalocean_get_trigger(namespace_id: str, trigger_name: str) -> str:
        if not namespace_id or not trigger_name:
            return from_tool_error(ToolError("invalid_argument", "namespace_id and trigger_name are required"))
        client = client_factory()
        try:
            payload = await client.get(f"/v2/functions/namespaces/{namespace_id}/triggers/{trigger_name}")
        except ToolError as err:
            return from_tool_error(err)
        trigger = (payload or {}).get("trigger", payload)
        return dumps(trigger)

    @mcp.tool(
        description="Update one or more fields of an existing trigger. Only the fields given are sent.",
    )
    async def digitalocean_update_trigger(
        namespace_id: str,
        trigger_name: str,
        function: str | None = None,
        type: str | None = None,
        is_enabled: bool | None = None,
        scheduled_details: dict[str, Any] | None = None,
    ) -> str:
        if not namespace_id or not trigger_name:
            return from_tool_error(ToolError("invalid_argument", "namespace_id and trigger_name are required"))
        body: dict[str, Any] = {}
        if function is not None:
            body["function"] = function
        if type is not None:
            body["type"] = type
        if is_enabled is not None:
            body["is_enabled"] = is_enabled
        if scheduled_details is not None:
            body["scheduled_details"] = scheduled_details
        if not body:
            return from_tool_error(ToolError("invalid_argument", "at least one updatable field is required"))
        client = client_factory()
        try:
            payload = await client.put(f"/v2/functions/namespaces/{namespace_id}/triggers/{trigger_name}", body)
        except ToolError as err:
            return from_tool_error(err)
        trigger = (payload or {}).get("trigger", payload)
        return dumps(trigger)

    @mcp.tool(
        description="Delete a trigger by name. Requires an explicit trigger_name; there is no wildcard delete.",
        annotations=ToolAnnotations(destructiveHint=True),
    )
    async def digitalocean_delete_trigger(namespace_id: str, trigger_name: str | None = None) -> str:
        if not namespace_id or not trigger_name:
            return from_tool_error(ToolError("invalid_argument", "namespace_id and trigger_name are required"))
        client = client_factory()
        try:
            await client.delete(f"/v2/functions/namespaces/{namespace_id}/triggers/{trigger_name}")
        except ToolError as err:
            return from_tool_error(err)
        return dumps({"deleted": True, "namespace_id": namespace_id, "trigger_name": trigger_name})

    return {
        "digitalocean_list_triggers": digitalocean_list_triggers,
        "digitalocean_create_trigger": digitalocean_create_trigger,
        "digitalocean_get_trigger": digitalocean_get_trigger,
        "digitalocean_update_trigger": digitalocean_update_trigger,
        "digitalocean_delete_trigger": digitalocean_delete_trigger,
    }
