import pytest

SAMPLE_FLAG = {
    "key": "checkout-v2",
    "enabled": True,
    "variations": [False, True],
    "default_variation": 0,
    "rules": [],
    "rollout": None,
}


async def test_list_flags_empty(client):
    resp = await client.get("/api/flags")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_flag(client):
    resp = await client.post("/api/flags", json=SAMPLE_FLAG)
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"] == "checkout-v2"
    assert body["enabled"] is True
    assert "updated_at" in body


async def test_create_duplicate_returns_409(client):
    await client.post("/api/flags", json=SAMPLE_FLAG)
    resp = await client.post("/api/flags", json=SAMPLE_FLAG)
    assert resp.status_code == 409


async def test_get_flag(client):
    await client.post("/api/flags", json=SAMPLE_FLAG)
    resp = await client.get("/api/flags/checkout-v2")
    assert resp.status_code == 200
    assert resp.json()["key"] == "checkout-v2"


async def test_get_flag_not_found(client):
    resp = await client.get("/api/flags/nonexistent")
    assert resp.status_code == 404


async def test_update_flag_toggle(client):
    await client.post("/api/flags", json=SAMPLE_FLAG)
    resp = await client.put("/api/flags/checkout-v2", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


async def test_delete_flag(client):
    await client.post("/api/flags", json=SAMPLE_FLAG)
    resp = await client.delete("/api/flags/checkout-v2")
    assert resp.status_code == 204
    resp2 = await client.get("/api/flags/checkout-v2")
    assert resp2.status_code == 404
