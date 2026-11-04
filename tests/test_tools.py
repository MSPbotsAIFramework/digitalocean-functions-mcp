import json

import httpx
import pytest

from digitalocean_functions_mcp.middleware import credential_context

from conftest import BASE_URL, TOKEN_A

pytestmark = pytest.mark.usefixtures("tools")


@pytest.fixture(autouse=True)
def _token():
    with credential_context(TOKEN_A):
        yield


# ---- namespaces -------------------------------------------------------


async def test_list_namespaces_returns_upstream_items(tools, respx_mock):
    upstream = [
        {"namespace_id": "fn-1", "label": "a", "region": "nyc1"},
        {"namespace_id": "fn-2", "label": "b", "region": "ams3"},
    ]
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces").mock(
        return_value=httpx.Response(200, json={"namespaces": upstream})
    )
    result = json.loads(await tools["digitalocean_list_namespaces"]())
    assert result == {"namespaces": upstream}


async def test_list_namespaces_empty_is_not_error(tools, respx_mock):
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces").mock(
        return_value=httpx.Response(200, json={"namespaces": []})
    )
    result = json.loads(await tools["digitalocean_list_namespaces"]())
    assert result == {"namespaces": []}
    assert "error" not in result


async def test_create_namespace_posts_label_and_region(tools, respx_mock):
    route = respx_mock.post(f"{BASE_URL}/v2/functions/namespaces").mock(
        return_value=httpx.Response(
            200, json={"namespace": {"namespace_id": "fn-new", "label": "my-fns", "region": "nyc1"}}
        )
    )
    result = json.loads(await tools["digitalocean_create_namespace"](label="my-fns", region="nyc1"))
    assert result == {"namespace_id": "fn-new", "label": "my-fns", "region": "nyc1"}
    assert json.loads(route.calls[0].request.content) == {"label": "my-fns", "region": "nyc1"}


async def test_create_namespace_missing_region_is_invalid_argument(tools, respx_mock):
    route = respx_mock.post(f"{BASE_URL}/v2/functions/namespaces")
    result = json.loads(await tools["digitalocean_create_namespace"](label="my-fns"))
    assert result["error"]["code"] == "invalid_argument"
    assert not route.called


async def test_get_namespace_returns_details(tools, respx_mock):
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces/fn-1").mock(
        return_value=httpx.Response(200, json={"namespace": {"namespace_id": "fn-1", "label": "a", "region": "nyc1"}})
    )
    result = json.loads(await tools["digitalocean_get_namespace"](namespace_id="fn-1"))
    assert result == {"namespace_id": "fn-1", "label": "a", "region": "nyc1"}


async def test_get_namespace_not_found_is_mapped(tools, respx_mock):
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces/missing").mock(
        return_value=httpx.Response(404, json={"message": "namespace not found"})
    )
    result = json.loads(await tools["digitalocean_get_namespace"](namespace_id="missing"))
    assert result["error"]["code"] == "not_found"
    assert result["error"]["retryable"] is False


async def test_delete_namespace_deletes_given_id(tools, respx_mock):
    route = respx_mock.delete(f"{BASE_URL}/v2/functions/namespaces/fn-1").mock(return_value=httpx.Response(204))
    result = json.loads(await tools["digitalocean_delete_namespace"](namespace_id="fn-1"))
    assert result == {"deleted": True, "namespace_id": "fn-1"}
    assert route.called


async def test_delete_namespace_requires_explicit_id(tools, respx_mock):
    route = respx_mock.delete(url__regex=r".*/v2/functions/namespaces/.*")
    result = json.loads(await tools["digitalocean_delete_namespace"]())
    assert result["error"]["code"] == "invalid_argument"
    assert not route.called


# ---- triggers -----------------------------------------------------------


async def test_list_triggers_returns_upstream_items(tools, respx_mock):
    upstream = [{"name": "t1"}, {"name": "t2"}]
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces/fn-1/triggers").mock(
        return_value=httpx.Response(200, json={"triggers": upstream})
    )
    result = json.loads(await tools["digitalocean_list_triggers"](namespace_id="fn-1"))
    assert result == {"triggers": upstream}


async def test_list_triggers_empty_is_not_error(tools, respx_mock):
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces/fn-1/triggers").mock(
        return_value=httpx.Response(200, json={"triggers": []})
    )
    result = json.loads(await tools["digitalocean_list_triggers"](namespace_id="fn-1"))
    assert result == {"triggers": []}


async def test_create_trigger_posts_full_body(tools, respx_mock):
    scheduled = {"cron": "*/5 * * * *"}
    route = respx_mock.post(f"{BASE_URL}/v2/functions/namespaces/fn-1/triggers").mock(
        return_value=httpx.Response(
            200,
            json={
                "trigger": {
                    "name": "every5min",
                    "function": "my-func",
                    "type": "SCHEDULED",
                    "is_enabled": True,
                    "scheduled_details": scheduled,
                }
            },
        )
    )
    result = json.loads(
        await tools["digitalocean_create_trigger"](
            namespace_id="fn-1",
            name="every5min",
            function="my-func",
            type="SCHEDULED",
            is_enabled=True,
            scheduled_details=scheduled,
        )
    )
    assert result["name"] == "every5min"
    sent = json.loads(route.calls[0].request.content)
    assert sent == {
        "name": "every5min",
        "function": "my-func",
        "type": "SCHEDULED",
        "is_enabled": True,
        "scheduled_details": scheduled,
    }


async def test_create_trigger_missing_required_field_is_invalid_argument(tools, respx_mock):
    route = respx_mock.post(f"{BASE_URL}/v2/functions/namespaces/fn-1/triggers")
    result = json.loads(
        await tools["digitalocean_create_trigger"](namespace_id="fn-1", name="t1", function="my-func", type=None)
    )
    assert result["error"]["code"] == "invalid_argument"
    assert "type" in result["error"]["message"]
    assert not route.called


async def test_get_trigger_returns_details(tools, respx_mock):
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces/fn-1/triggers/t1").mock(
        return_value=httpx.Response(200, json={"trigger": {"name": "t1", "function": "my-func"}})
    )
    result = json.loads(await tools["digitalocean_get_trigger"](namespace_id="fn-1", trigger_name="t1"))
    assert result == {"name": "t1", "function": "my-func"}


async def test_get_trigger_not_found_is_mapped(tools, respx_mock):
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces/fn-1/triggers/missing").mock(
        return_value=httpx.Response(404, json={"message": "trigger not found"})
    )
    result = json.loads(await tools["digitalocean_get_trigger"](namespace_id="fn-1", trigger_name="missing"))
    assert result["error"]["code"] == "not_found"


async def test_update_trigger_sends_only_given_fields(tools, respx_mock):
    route = respx_mock.put(f"{BASE_URL}/v2/functions/namespaces/fn-1/triggers/t1").mock(
        return_value=httpx.Response(200, json={"trigger": {"name": "t1", "is_enabled": False}})
    )
    result = json.loads(
        await tools["digitalocean_update_trigger"](namespace_id="fn-1", trigger_name="t1", is_enabled=False)
    )
    assert result == {"name": "t1", "is_enabled": False}
    sent = json.loads(route.calls[0].request.content)
    assert sent == {"is_enabled": False}


async def test_delete_trigger_deletes_named_trigger(tools, respx_mock):
    route = respx_mock.delete(f"{BASE_URL}/v2/functions/namespaces/fn-1/triggers/t1").mock(
        return_value=httpx.Response(204)
    )
    result = json.loads(await tools["digitalocean_delete_trigger"](namespace_id="fn-1", trigger_name="t1"))
    assert result == {"deleted": True, "namespace_id": "fn-1", "trigger_name": "t1"}
    assert route.called


async def test_delete_trigger_requires_explicit_name(tools, respx_mock):
    route = respx_mock.delete(url__regex=r".*/triggers/.*")
    result = json.loads(await tools["digitalocean_delete_trigger"](namespace_id="fn-1"))
    assert result["error"]["code"] == "invalid_argument"
    assert not route.called


# ---- access keys ----------------------------------------------------------


async def test_list_access_keys_returns_upstream_items(tools, respx_mock):
    upstream = [{"key_id": "k1"}, {"key_id": "k2"}]
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces/fn-1/access-keys").mock(
        return_value=httpx.Response(200, json={"keys": upstream})
    )
    result = json.loads(await tools["digitalocean_list_access_keys"](namespace_id="fn-1"))
    assert result == {"keys": upstream}


async def test_create_access_key_value_not_logged(tools, respx_mock, caplog):
    secret_value = "do_key_secret_value_do_not_log_me"
    respx_mock.post(f"{BASE_URL}/v2/functions/namespaces/fn-1/access-keys").mock(
        return_value=httpx.Response(200, json={"key": {"key_id": "k1", "name": "ci", "value": secret_value}})
    )
    with caplog.at_level("DEBUG"):
        result = json.loads(await tools["digitalocean_create_access_key"](namespace_id="fn-1", name="ci"))

    assert result["value"] == secret_value  # returned to the caller (AC11) ...
    for record in caplog.records:  # ... but never written to our own logs
        assert secret_value not in record.getMessage()


async def test_update_access_key_applies_update(tools, respx_mock):
    route = respx_mock.put(f"{BASE_URL}/v2/functions/namespaces/fn-1/access-keys/k1").mock(
        return_value=httpx.Response(200, json={"key": {"key_id": "k1", "name": "renamed"}})
    )
    result = json.loads(
        await tools["digitalocean_update_access_key"](namespace_id="fn-1", key_id="k1", name="renamed")
    )
    assert result == {"key_id": "k1", "name": "renamed"}
    sent = json.loads(route.calls[0].request.content)
    assert sent == {"name": "renamed"}


async def test_delete_access_key_deletes_given_id(tools, respx_mock):
    route = respx_mock.delete(f"{BASE_URL}/v2/functions/namespaces/fn-1/access-keys/k1").mock(
        return_value=httpx.Response(204)
    )
    result = json.loads(await tools["digitalocean_delete_access_key"](namespace_id="fn-1", key_id="k1"))
    assert result == {"deleted": True, "namespace_id": "fn-1", "key_id": "k1"}
    assert route.called


async def test_delete_access_key_requires_explicit_id(tools, respx_mock):
    route = respx_mock.delete(url__regex=r".*/access-keys/.*")
    result = json.loads(await tools["digitalocean_delete_access_key"](namespace_id="fn-1"))
    assert result["error"]["code"] == "invalid_argument"
    assert not route.called


# ---- network robustness (AC16) --------------------------------------------


async def test_transient_429_is_retried_then_succeeds(tools, respx_mock):
    route = respx_mock.get(f"{BASE_URL}/v2/functions/namespaces")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0"}, json={"message": "rate limited"}),
        httpx.Response(200, json={"namespaces": [{"namespace_id": "fn-1"}]}),
    ]
    result = json.loads(await tools["digitalocean_list_namespaces"]())
    assert result == {"namespaces": [{"namespace_id": "fn-1"}]}
    assert route.call_count == 2


async def test_sustained_5xx_returns_bounded_upstream_error(tools, respx_mock):
    respx_mock.get(f"{BASE_URL}/v2/functions/namespaces").mock(
        return_value=httpx.Response(503, json={"message": "down for maintenance"})
    )
    import time

    start = time.monotonic()
    result = json.loads(await tools["digitalocean_list_namespaces"]())
    elapsed = time.monotonic() - start

    assert result["error"]["code"] == "upstream_error"
    assert result["error"]["retryable"] is True
    assert elapsed < 120  # SOP S5 time budget; the mocked Retry-After keeps this test fast


# ---- tools/list shape (AC19) -----------------------------------------------


async def test_tools_list_semantic_hints_snapshot(mcp, tools):
    tool_list = await mcp.list_tools()
    by_name = {t.name: t for t in tool_list}
    assert set(by_name) == set(tools)

    for name, tool in by_name.items():
        if name.startswith("digitalocean_list_") or name.startswith("digitalocean_get_"):
            assert tool.annotations is not None and tool.annotations.readOnlyHint is True, name
        if name.startswith("digitalocean_delete_"):
            assert tool.annotations is not None and tool.annotations.destructiveHint is True, name
