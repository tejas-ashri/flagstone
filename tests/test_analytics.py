import pytest


@pytest.mark.asyncio
async def test_experiment_results_conversion_rate(client):
    await client.post("/api/flags", json={
        "key": "checkout", "enabled": True, "variations": ["control", "variant"],
        "default_variation": 0, "rules": [], "rollout": None
    })
    events = (
        [{"flag_key": "checkout", "event_type": "exposure", "variation_index": 0, "user_id": f"u{i}"} for i in range(50)] +
        [{"flag_key": "checkout", "event_type": "exposure", "variation_index": 1, "user_id": f"v{i}"} for i in range(50)] +
        [{"flag_key": "checkout", "event_type": "conversion", "variation_index": 1, "user_id": f"v{i}"} for i in range(10)]
    )
    await client.post("/sdk/events", json={"events": events}, headers={"x-sdk-key": "sdk-dev-key"})
    resp = await client.get("/api/experiments/checkout/results")
    assert resp.status_code == 200
    results = {r["variation_index"]: r for r in resp.json()["variations"]}
    assert results[0]["conversion_rate_pct"] == 0.0
    assert results[1]["conversion_rate_pct"] == 20.0


@pytest.mark.asyncio
async def test_experiment_results_empty(client):
    await client.post("/api/flags", json={
        "key": "empty-exp", "enabled": True, "variations": [False, True],
        "default_variation": 0, "rules": [], "rollout": None
    })
    resp = await client.get("/api/experiments/empty-exp/results")
    assert resp.status_code == 200
    assert resp.json()["variations"] == []
