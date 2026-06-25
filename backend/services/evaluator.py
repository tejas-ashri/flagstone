from backend.services.bucketing import in_rollout

def evaluate(flag: dict, user: dict) -> int:
    if not flag.get("enabled", True):
        return flag.get("default_variation", 0)
    for rule in flag.get("rules", []):
        if _match_rule(rule, user):
            return rule["variation"]
    rollout = flag.get("rollout")
    if rollout:
        user_id = user.get("id", "")
        if in_rollout(flag["key"], user_id, rollout["percentage"]):
            return rollout["variation"]
    return flag.get("default_variation", 0)

def _match_rule(rule: dict, user: dict) -> bool:
    attr = user.get(rule["attribute"])
    op = rule["operator"]
    val = rule["value"]
    if op == "equals":   return attr == val
    if op == "contains": return isinstance(attr, str) and val in attr
    if op == "gt":       return isinstance(attr, (int, float)) and attr > val
    if op == "lt":       return isinstance(attr, (int, float)) and attr < val
    if op == "in":       return attr in val
    return False
