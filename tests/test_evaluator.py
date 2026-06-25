import pytest
from backend.services.evaluator import evaluate as backend_evaluate
from sdk.evaluator import evaluate as sdk_evaluate

BASE_FLAG = {
    "key": "test-flag",
    "enabled": True,
    "variations": [False, True],
    "default_variation": 0,
    "rules": [],
    "rollout": None,
}

def flag(**overrides):
    return {**BASE_FLAG, **overrides}

def test_disabled_flag_returns_default():
    f = flag(enabled=False)
    assert backend_evaluate(f, {"id": "u1"}) == 0

def test_disabled_flag_ignores_rules():
    f = flag(
        enabled=False,
        rules=[{"attribute": "plan", "operator": "equals", "value": "enterprise", "variation": 1}],
    )
    assert backend_evaluate(f, {"id": "u1", "plan": "enterprise"}) == 0

def test_rule_equals_match():
    f = flag(rules=[{"attribute": "plan", "operator": "equals", "value": "enterprise", "variation": 1}])
    assert backend_evaluate(f, {"id": "u1", "plan": "enterprise"}) == 1

def test_rule_equals_no_match():
    f = flag(rules=[{"attribute": "plan", "operator": "equals", "value": "enterprise", "variation": 1}])
    assert backend_evaluate(f, {"id": "u1", "plan": "free"}) == 0

def test_rule_contains_operator():
    f = flag(rules=[{"attribute": "email", "operator": "contains", "value": "@enterprise.com", "variation": 1}])
    assert backend_evaluate(f, {"id": "u1", "email": "user@enterprise.com"}) == 1
    assert backend_evaluate(f, {"id": "u1", "email": "user@gmail.com"}) == 0

def test_rule_in_operator():
    f = flag(rules=[{"attribute": "country", "operator": "in", "value": ["US", "CA"], "variation": 1}])
    assert backend_evaluate(f, {"id": "u1", "country": "US"}) == 1
    assert backend_evaluate(f, {"id": "u1", "country": "DE"}) == 0

def test_rule_gt_operator():
    f = flag(rules=[{"attribute": "age", "operator": "gt", "value": 18, "variation": 1}])
    assert backend_evaluate(f, {"id": "u1", "age": 21}) == 1
    assert backend_evaluate(f, {"id": "u1", "age": 16}) == 0

def test_first_matching_rule_wins():
    f = flag(rules=[
        {"attribute": "plan", "operator": "equals", "value": "enterprise", "variation": 1},
        {"attribute": "plan", "operator": "equals", "value": "enterprise", "variation": 2},
    ])
    assert backend_evaluate(f, {"id": "u1", "plan": "enterprise"}) == 1

def test_rollout_100_percent():
    f = flag(rollout={"variation": 1, "percentage": 100})
    assert backend_evaluate(f, {"id": "u1"}) == 1

def test_rollout_0_percent():
    f = flag(rollout={"variation": 1, "percentage": 0})
    assert backend_evaluate(f, {"id": "u1"}) == 0

def test_no_rule_no_rollout_returns_default():
    assert backend_evaluate(BASE_FLAG, {"id": "u1"}) == 0

def test_backend_and_sdk_evaluate_match():
    f = flag(
        rules=[{"attribute": "plan", "operator": "equals", "value": "enterprise", "variation": 1}],
        rollout={"variation": 1, "percentage": 50},
    )
    user = {"id": "u_abc", "plan": "free"}
    assert backend_evaluate(f, user) == sdk_evaluate(f, user)
