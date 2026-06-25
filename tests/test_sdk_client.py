import respx
import httpx
import threading
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


@respx.mock
def test_is_enabled_buffers_exposure_event():
    respx.get("http://localhost:8000/sdk/config").mock(
        return_value=httpx.Response(200, json=FLAG_CONFIG)
    )
    client = FlagClient("sdk-key", base_url="http://localhost:8000", poll_interval=9999, flush_interval=9999)
    client.is_enabled("checkout-v2", {"id": "u1", "plan": "enterprise"})
    with client._flush_lock:
        buffer = list(client._event_buffer)
    assert len(buffer) == 1
    assert buffer[0]["event_type"] == "exposure"
    assert buffer[0]["flag_key"] == "checkout-v2"
    assert buffer[0]["user_id"] == "u1"
    client.close()


@respx.mock
def test_track_conversion_buffers_conversion_event():
    respx.get("http://localhost:8000/sdk/config").mock(
        return_value=httpx.Response(200, json=FLAG_CONFIG)
    )
    client = FlagClient("sdk-key", base_url="http://localhost:8000", poll_interval=9999, flush_interval=9999)
    client.track_conversion("checkout-v2", {"id": "u1", "plan": "enterprise"})
    with client._flush_lock:
        buffer = list(client._event_buffer)
    assert len(buffer) == 1
    assert buffer[0]["event_type"] == "conversion"
    assert buffer[0]["flag_key"] == "checkout-v2"
    client.close()


@respx.mock
def test_flush_triggered_at_100_events():
    respx.get("http://localhost:8000/sdk/config").mock(
        return_value=httpx.Response(200, json=FLAG_CONFIG)
    )
    flush_route = respx.post("http://localhost:8000/sdk/events").mock(
        return_value=httpx.Response(202, json={"accepted": 100})
    )
    client = FlagClient("sdk-key", base_url="http://localhost:8000", poll_interval=9999, flush_interval=9999)
    # Fill buffer to 100 — triggers automatic flush on the 100th event
    for i in range(100):
        client._buffer_event("exposure", "checkout-v2", 0, {"id": f"u{i}"})
    assert flush_route.called
    with client._flush_lock:
        assert len(client._event_buffer) == 0
    client.close()


@respx.mock
def test_close_cancels_flush_timer():
    respx.get("http://localhost:8000/sdk/config").mock(
        return_value=httpx.Response(200, json=FLAG_CONFIG)
    )
    client = FlagClient("sdk-key", base_url="http://localhost:8000", poll_interval=9999, flush_interval=9999)
    timer = client._flush_timer
    client.close()
    # Timer should be cancelled (not alive)
    assert not timer.is_alive()
