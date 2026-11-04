"""Tool-result serialization: compact JSON, no ASCII-escaping, defensive
size cap (SOP S2.5). None of this connector's list endpoints are documented
by DigitalOcean as paginated, so the cap is a defensive fallback, not the
normal path.
"""

import json

MAX_RESPONSE_CHARS = 20000


def dumps(payload: object) -> str:
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if len(text) <= MAX_RESPONSE_CHARS:
        return text
    return _truncate(payload, text)


def _truncate(payload: object, text: str) -> str:
    if isinstance(payload, dict):
        list_keys = [k for k, v in payload.items() if isinstance(v, list)]
        if list_keys:
            key = list_keys[0]
            items = list(payload[key])
            while items:
                items = items[: max(1, len(items) // 2)]
                candidate = dict(payload)
                candidate[key] = items
                candidate["has_more"] = True
                candidate_text = json.dumps(candidate, separators=(",", ":"), ensure_ascii=False)
                if len(candidate_text) <= MAX_RESPONSE_CHARS:
                    return candidate_text
                if len(items) == 1:
                    break
    # Nothing structured to shrink -- fall back to a hard cut. This keeps the
    # response under the byte budget; it is not expected to be hit in
    # practice since DigitalOcean's Functions API documents no pagination
    # for namespaces/triggers/access-keys.
    return text[:MAX_RESPONSE_CHARS]
