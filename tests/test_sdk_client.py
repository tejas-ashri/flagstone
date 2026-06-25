import respx
import httpx
import threading
from sdk.client import FlagClient
from sdk.disk_cache import DiskCache

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


def test_disk_cache_write_and_read(tmp_path):
    cache = DiskCache(str(tmp_path / "cache.json"))
    config = {"flags": {"my-flag": {"key": "my-flag", "enabled": True, "variations": [False, True], "default_variation": 1, "rules": [], "rollout": None}}}
    cache.write(config)
    result = cache.read()
    assert result == config


def test_disk_cache_returns_none_when_missing(tmp_path):
    cache = DiskCache(str(tmp_path / "cache.json"))
    assert cache.read() is None


def test_disk_cache_returns_none_on_corrupt_file(tmp_path):
    p = tmp_path / "cache.json"
    p.write_text("not json")
    cache = DiskCache(str(p))
    assert cache.read() is None


@respx.mock
def test_client_falls_back_to_disk_cache(tmp_path):
    config = {"flags": {"my-flag": {"key": "my-flag", "enabled": True, "variations": [False, True], "default_variation": 1, "rules": [], "rollout": None}}}
    cache = DiskCache(str(tmp_path / "cache.json"))
    cache.write(config)
    respx.get("http://localhost:8000/sdk/config").mock(side_effect=httpx.ConnectError("unreachable"))
    client = FlagClient("sdk-key", cache_path=str(tmp_path / "cache.json"), poll_interval=9999)
    assert client.is_enabled("my-flag", {"id": "u1"}) is True
    client.close()


@respx.mock
def test_client_writes_cache_on_successful_fetch(tmp_path):
    config = {"flags": {}}
    respx.get("http://localhost:8000/sdk/config").mock(return_value=httpx.Response(200, json=config))
    cache_path = str(tmp_path / "cache.json")
    client = FlagClient("sdk-key", cache_path=cache_path, poll_interval=9999)
    cache = DiskCache(cache_path)
    assert cache.read() == config
    client.close()
