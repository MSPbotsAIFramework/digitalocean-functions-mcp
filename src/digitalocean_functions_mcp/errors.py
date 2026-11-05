"""Structured tool error envelope.

Tools never raise. Every failure is returned as a JSON string:
    {"error": {"code": "<code>", "message": "<human readable>", "retryable": bool}}

`code` is drawn from a fixed, closed vocabulary (SOP S4.2) so callers can
branch programmatically instead of parsing free-text messages.
"""

import json

# code -> default retryable flag
_RETRYABLE = {
    "not_configured": False,
    "unauthorized": False,
    "not_found": False,
    "invalid_argument": False,
    "rate_limited": True,
    "upstream_error": True,
}


class ToolError(Exception):
    """Raised internally by the API client / tools, caught at the tool boundary
    and converted to the JSON error envelope. Never escapes a tool function."""

    def __init__(self, code: str, message: str, retryable: bool | None = None):
        if code not in _RETRYABLE:
            raise ValueError(f"unknown error code: {code}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = _RETRYABLE[code] if retryable is None else retryable


def error_envelope(code: str, message: str, retryable: bool | None = None) -> str:
    err = ToolError(code, message, retryable)
    return json.dumps(
        {"error": {"code": err.code, "message": err.message, "retryable": err.retryable}},
        separators=(",", ":"),
        ensure_ascii=False,
    )


def from_tool_error(err: ToolError) -> str:
    return error_envelope(err.code, err.message, err.retryable)


def map_status_code(status_code: int, message: str) -> ToolError:
    """Map a DigitalOcean HTTP status code onto the fixed error vocabulary."""
    if status_code in (401, 403):
        return ToolError("unauthorized", message)
    if status_code == 404:
        return ToolError("not_found", message)
    if status_code in (400, 422):
        return ToolError("invalid_argument", message)
    if status_code == 429:
        return ToolError("rate_limited", message)
    if status_code >= 500:
        return ToolError("upstream_error", message)
    return ToolError("upstream_error", message)
