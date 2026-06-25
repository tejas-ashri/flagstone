import pytest


async def test_sdk_config_returns_flags(client):
    await client.post("/api/flags", json={
        "key": "my-flag", "enabled": True, "variations": [False, True],
        "default_variation": 0, "rules": [], "rollout": None,
    })
    resp = await client.get("/sdk/config", headers={"x-sdk-key": "sdk-dev-key"})
    assert resp.status_code == 200
    body = resp.json()
    assert "flags" in body
    assert "my-flag" in body["flags"]


async def test_sdk_config_requires_key(client):
    resp = await client.get("/sdk/config")
    assert resp.status_code == 422
