import pytest
from backend.services.bucketing import bucket as backend_bucket, in_rollout as backend_in_rollout
from sdk.bucketing import bucket as sdk_bucket, in_rollout as sdk_in_rollout

CASES = [
    ("new-checkout", "u_1", None),
    ("new-checkout", "u_100", None),
    ("other-flag", "u_1", None),
]

@pytest.mark.parametrize("flag_key,user_id,_", CASES)
def test_backend_and_sdk_bucket_match(flag_key, user_id, _):
    assert backend_bucket(flag_key, user_id) == sdk_bucket(flag_key, user_id)

def test_bucket_is_in_0_to_99():
    b = backend_bucket("flag", "user")
    assert 0 <= b <= 99

def test_in_rollout_100_percent_always_true():
    assert backend_in_rollout("flag", "user", 100) is True

def test_in_rollout_0_percent_always_false():
    assert backend_in_rollout("flag", "user", 0) is False

def test_in_rollout_boundary():
    b = backend_bucket("flag", "boundary-user")
    assert backend_in_rollout("flag", "boundary-user", b + 1) is True
    assert backend_in_rollout("flag", "boundary-user", b) is False
