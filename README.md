# digitalocean-functions-mcp

MCP server exposing [DigitalOcean Functions](https://docs.digitalocean.com/products/functions/) to MSPbots Agent platform clients (Claude, ChatGPT, Cursor, or any MCP-compatible AI client).

It lets an agent manage a DigitalOcean account's Functions **namespaces**, their **triggers**, and their **namespace access keys** through DigitalOcean's public REST API. Deploying or invoking the function code itself (packages/actions) is out of scope for this connector — see [Non-goals](#non-goals).

Transport: MCP Streamable HTTP. Stack: Python 3.12, [FastMCP](https://github.com/modelcontextprotocol/python-sdk), httpx. License: Apache-2.0.

---

<div align="center">

## MSPbots Connector

**The MCP Gateway built for MSPs: visible, controlled, and your data stays where it belongs.**

[**Get started at connect.mspbots.ai →**](https://connect.mspbots.ai)

</div>

---

MSPbots Connector gives your AI clients one MCP URL to reach your entire MSP stack (RMM, PSA, documentation, security, finance), and gives you control over who can call which tool and a record of everything that was called.

**Hosted service: [connect.mspbots.ai](https://connect.mspbots.ai)** · Free to use.

### Why Connector

![MSPbots Connector](https://stgoss.mspbots.ai/files/mcp/mspbots-mcp.png)

| | |
|---|---|
| **Visible** | Every tool call is logged: who, which vendor, when. Usage dashboard, CSV export, SIEM streaming. |
| **Controlled** | Role-based, per-tool allowlist. Deny by default. |
| **Protected** | Credentials encrypted per record. AI clients never see your vendor passwords or tokens. |
| **MSP-native** | Built for the MSP stack only: RMM, PSA, documentation, security, finance. |

### Quick start

1. **Sign up** at [connect.mspbots.ai](https://connect.mspbots.ai).
2. **Connect your vendors.** Pick from 150+ connectors and authorize each one on the vendor's own page, or bring your own API keys. No extra vendor accounts needed.
3. **Set access.** Create roles and decide which tools each role may call. Nothing is allowed until you allow it.
4. **Add your MCP URL to your AI client.** Copy the URL from your Connector dashboard into Claude, ChatGPT, Cursor, VS Code, Gemini, Codex, or any MCP-capable client.
5. **Ask your AI to do real work**, and watch every call appear in the audit log.

### Features

**Unified gateway**
- One MCP URL for all your AI clients
- 150+ connectors across the MSP stack
- Custom MCP servers supported, free
- Authorization happens on each vendor's own page; the AI never sees passwords or tokens
- Bring your own credentials: use the vendor API keys you already have
- Multiple accounts per app; connect once, reuse across AI clients
- Tool search: finds the right action for the task
- One sign-in; vendor credentials are injected behind the scenes and OAuth tokens refresh automatically

**Visibility**
- Audit log for every tool call (who, which vendor, when)
- Usage dashboard: call volume, top vendors, error rate, per-user activity
- Export audit logs to CSV, or stream to Loki, Graylog, or LogScale (SIEM)
- Optional recording of tool arguments and result summaries (off by default, enabled per organization)

**Control**
- Per-role, per-tool allowlist, deny by default
- owner / admin / member roles
- SCIM provisioning with Entra ID, Okta, JumpCloud, and Google Workspace

**Security**
- Credentials encrypted one record at a time (AES-256-GCM, per-record key)
- AI clients authenticate with OAuth 2.1 + PKCE
- Vendor responses are scanned for prompt-injection patterns and returned as structured data. This is one layer of defense, not a guarantee against every attack.
- Static egress IP for customer firewall and API allowlisting

### Pricing

**Free.**

Links: [connect.mspbots.ai](https://connect.mspbots.ai) · [mspbots.ai](https://mspbots.ai)

---

## Authentication headers

Every request to `/mcp` must carry the caller's own DigitalOcean credential — this service never stores or shares credentials across requests.

| Header | Required | Meaning | Where to get it |
|---|---|---|---|
| `X-Digitalocean-Token` | Yes | A DigitalOcean Personal Access Token with Functions read/write scope | DigitalOcean control panel → **API** → **Tokens** → Generate New Token |

Missing the header returns `401` with a body listing the required header name.

## Non-goals

- Deploying, updating, or invoking function code (packages/actions) via a namespace's own OpenWhisk-compatible API host. That surface needs a different credential (a namespace access key, itself created by this connector's `digitalocean_create_access_key` tool) and a per-namespace base URL. Could be a v2 if ever requested.
- Any DigitalOcean resource outside Functions (Droplets, Spaces, Databases, etc.).

## Tools

13 tools, one per DigitalOcean Functions REST endpoint:

| Tool | Description | Annotations |
|---|---|---|
| `digitalocean_list_namespaces` | List the DigitalOcean Functions namespaces visible to the caller's token. | read-only |
| `digitalocean_create_namespace` | Create a namespace. Requires `label` and `region`. | — |
| `digitalocean_get_namespace` | Get a namespace's details by id. | read-only |
| `digitalocean_delete_namespace` | Delete a namespace and everything in it. Requires an explicit `namespace_id`. | destructive |
| `digitalocean_list_triggers` | List the triggers configured on a namespace. | read-only |
| `digitalocean_create_trigger` | Create a trigger. Requires `name`, `function`, `type`. | — |
| `digitalocean_get_trigger` | Get a trigger's details by name. | read-only |
| `digitalocean_update_trigger` | Update one or more fields of an existing trigger. | — |
| `digitalocean_delete_trigger` | Delete a trigger by name. Requires an explicit `trigger_name`. | destructive |
| `digitalocean_list_access_keys` | List the namespace access keys for a namespace. | read-only |
| `digitalocean_create_access_key` | Create a namespace access key. Requires a `name`. | — |
| `digitalocean_update_access_key` | Update a namespace access key by id. | — |
| `digitalocean_delete_access_key` | Delete a namespace access key by id. Requires an explicit `key_id`. | destructive |

Errors are returned as a structured envelope: `{"error": {"code", "message", "retryable"}}`, with `code` drawn from `not_configured | unauthorized | not_found | invalid_argument | rate_limited | upstream_error`.

## Local development

```bash
uv sync
uv run pytest
uv run python -m digitalocean_functions_mcp   # listens on 0.0.0.0:8080
```

Try it with a real token:

```bash
curl -X POST http://localhost:8080/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H 'X-Digitalocean-Token: <your DigitalOcean PAT>' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Docker:

```bash
docker build --platform linux/amd64 -t digitalocean-functions-mcp:dev .
docker run --rm -p 8080:8080 digitalocean-functions-mcp:dev
```
