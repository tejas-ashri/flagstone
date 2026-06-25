import pytest


@pytest.mark.asyncio
async def test_ingest_events_accepted(client):
    await client.post("/api/flags", json={
        "key": "checkout", "enabled": True, "variations": [False, True],
        "default_variation": 0, "rules": [], "rollout": None
    })
    resp = await client.post("/sdk/events", json={
        "events": [
            {"flag_key": "checkout", "event_type": "exposure", "variation_index": 0, "user_id": "u1"},
            {"flag_key": "checkout", "event_type": "exposure", "variation_index": 1, "user_id": "u2"},
        ]
    }, headers={"x-sdk-key": "sdk-dev-key"})
    assert resp.status_code == 202
    assert resp.json()["accepted"] == 2


@pytest.mark.asyncio
async def test_ingest_rejects_oversized_batch(client):
    resp = await client.post("/sdk/events", json={
        "events": [
            {"flag_key": "f", "event_type": "exposure", "variation_index": 0, "user_id": f"u{i}"}
            for i in range(1001)
        ]
    }, headers={"x-sdk-key": "sdk-dev-key"})
    assert resp.status_code == 422
