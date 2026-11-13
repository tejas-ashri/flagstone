"""Explains why a user gets a variation, for the admin "test a user" tool.

The variation always comes from evaluator.evaluate (the same logic the SDK
runs); this module only reconstructs the reason alongside it.
"""

from backend.services.bucketing import bucket
from backend.services.evaluator import _match_rule, evaluate


def explain(flag: dict, user: dict) -> dict:
    variation = evaluate(flag, user)
    result: dict = {"variation_index": variation, "reason": "default"}
    if not flag.get("enabled", True):
        result["reason"] = "disabled"
        return result
    for i, rule in enumerate(flag.get("rules", [])):
        if _match_rule(rule, user):
            result.update(reason="rule", rule_index=i)
            return result
    rollout = flag.get("rollout")
    if rollout:
        b = bucket(flag["key"], user.get("id", ""))
        result.update(
            bucket=b,
            rollout_percentage=rollout["percentage"],
            reason="rollout" if b < rollout["percentage"] else "outside_rollout",
        )
    return result
