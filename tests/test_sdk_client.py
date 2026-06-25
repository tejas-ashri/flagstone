import respx
import httpx
from sdk.client import FlagClient

FLAG_CONFIG = {
    "flags": {
        "checkout-v2": {
            "key": "checkout-v2",
            "enabled": True,
            "variations": [False, True],
            "default_variation": 0,
            "rules": [{"attribute": "plan", "operator": "equals", "value": "enterprise", "variation": 1}],
            "rollout": {"variation": 1, "percentage": 20},
        }
    }
}


@respx.mock
def test_is_enabled_for_enterprise_user():
    respx.get("http://localhost:8000/sdk/config").mock(
        return_value=httpx.Response(200, json=FLAG_CONFIG)
    )
    client = FlagClient("sdk-key", base_url="http://localhost:8000", poll_interval=9999)
    assert client.is_enabled("checkout-v2", {"id": "u1", "plan": "enterprise"}) is True
    client.close()


@respx.mock
def test_is_enabled_false_for_free_user_not_in_rollout():
    # Find a user who buckets >= 20 for "checkout-v2"
    from sdk.bucketing import bucket
    uid = next(f"u{i}" for i in range(1000) if bucket("checkout-v2", f"u{i}") >= 20)
    respx.get("http://localhost:8000/sdk/config").mock(
        return_value=httpx.Response(200, json=FLAG_CONFIG)
    )
    client = FlagClient("sdk-key", base_url="http://localhost:8000", poll_interval=9999)
    assert client.is_enabled("checkout-v2", {"id": uid, "plan": "free"}) is False
    client.close()


@respx.mock
def test_unknown_flag_returns_false():
    respx.get("http://localhost:8000/sdk/config").mock(
        return_value=httpx.Response(200, json=FLAG_CONFIG)
    )
    client = FlagClient("sdk-key", base_url="http://localhost:8000", poll_interval=9999)
    assert client.is_enabled("nonexistent", {"id": "u1"}) is False
    client.close()
