import hashlib

def bucket(flag_key: str, user_id: str) -> int:
    raw = f"{flag_key}:{user_id}".encode()
    digest = hashlib.md5(raw).hexdigest()
    return int(digest[:8], 16) % 100

def in_rollout(flag_key: str, user_id: str, percentage: int) -> bool:
    return bucket(flag_key, user_id) < percentage
