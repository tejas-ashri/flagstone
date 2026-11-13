import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from backend.config import Settings, get_settings
from backend.services import auth_service
from backend.services.auth_service import Profile

from tests.conftest import make_client, sign_in_as

FLAG = {"key": "checkout", "variations": [False, True], "rules": [], "rollout": None}


async def new_project(client, name="Beta") -> str:
    resp = await client.post("/api/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def new_key(client, project_id) -> str:
    resp = await client.post(f"/api/projects/{project_id}/keys", json={"label": "test"})
    assert resp.status_code == 201
    return resp.json()["key"]


# Authentication


async def test_admin_api_requires_sign_in(anon_client):
    assert (await anon_client.get("/api/flags")).status_code == 401
    assert (await anon_client.get("/api/projects")).status_code == 401
    assert (await anon_client.get("/api/me")).status_code == 401


async def test_writes_require_csrf_header(app):
    token = await sign_in_as(app, "a@example.com", default_role="admin")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        cookies={"flagstone_session": token},
    ) as c:
        assert (await c.get("/api/flags")).status_code == 200
        assert (await c.post("/api/flags", json=FLAG)).status_code == 403


async def test_me_lists_projects(client):
    resp = await client.get("/api/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "admin@example.com"
    assert [p["id"] for p in body["projects"]] == ["default"]
    assert body["projects"][0]["role"] == "admin"


async def test_logout_ends_session(client):
    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/api/me")).status_code == 401


async def test_admin_emails_grants_default_admin(app):
    settings = Settings(admin_emails="Boss@Example.com")
    async with app.state.session_factory() as db:
        user = await auth_service.sign_in(
            db, Profile("github", "1", "boss@example.com", True), settings
        )
        token = await auth_service.create_session(db, user.id, settings)
    async with make_client(app, token) as c:
        assert (await c.post("/api/flags", json=FLAG)).status_code == 201


async def test_unverified_email_cannot_sign_in(app):
    async with app.state.session_factory() as db:
        with pytest.raises(ValueError):
            await auth_service.sign_in(
                db, Profile("github", "1", "x@example.com", False), Settings()
            )


async def test_same_email_links_providers(app):
    async with app.state.session_factory() as db:
        s = Settings()
        a = await auth_service.sign_in(db, Profile("github", "1", "p@example.com", True), s)
        b = await auth_service.sign_in(db, Profile("google", "g", "P@example.com", True), s)
        assert a.id == b.id
        assert await auth_service.identities_for(db, a.id) == ["github", "google"]


# Roles


async def test_viewer_can_read_but_not_write(app, client):
    await client.post("/api/flags", json=FLAG)
    token = await sign_in_as(app, "viewer@example.com", default_role="viewer")
    async with make_client(app, token) as viewer:
        assert (await viewer.get("/api/flags")).status_code == 200
        assert (await viewer.get("/api/experiments/checkout/results")).status_code == 200
        assert (await viewer.put("/api/flags/checkout", json={"enabled": False})).status_code == 403
        assert (await viewer.delete("/api/flags/checkout")).status_code == 403
        resp = await viewer.post("/api/projects/default/keys", json={"label": "x"})
        assert resp.status_code == 403


async def test_non_member_gets_404(app, client):
    project_id = await new_project(client)
    token = await sign_in_as(app, "outsider@example.com")
    async with make_client(app, token) as outsider:
        assert (await outsider.get("/api/flags")).status_code == 404
        assert (await outsider.get(f"/api/projects/{project_id}/flags")).status_code == 404
        assert (await outsider.get(f"/api/projects/{project_id}")).status_code == 404


# Project isolation: an admin and an SDK key only reach their own project


async def test_sdk_key_only_sees_its_project(client):
    beta = await new_project(client)
    await client.post("/api/flags", json={**FLAG, "key": "default-only"})
    await client.post(f"/api/projects/{beta}/flags", json={**FLAG, "key": "beta-only"})
    beta_key = await new_key(client, beta)

    resp = await client.get("/sdk/config", headers={"x-sdk-key": beta_key})
    assert set(resp.json()["flags"]) == {"beta-only"}
    resp = await client.get("/sdk/config", headers={"x-sdk-key": "sdk-dev-key"})
    assert set(resp.json()["flags"]) == {"default-only"}


async def test_same_flag_key_in_two_projects(client):
    beta = await new_project(client)
    assert (await client.post("/api/flags", json=FLAG)).status_code == 201
    assert (await client.post(f"/api/projects/{beta}/flags", json=FLAG)).status_code == 201
    await client.put(f"/api/projects/{beta}/flags/checkout", json={"enabled": False})
    assert (await client.get("/api/flags/checkout")).json()["enabled"] is True
    assert (await client.get(f"/api/projects/{beta}/flags/checkout")).json()["enabled"] is False


async def test_events_cannot_target_other_projects(client):
    beta = await new_project(client)
    await client.post(f"/api/projects/{beta}/flags", json=FLAG)
    resp = await client.post(
        "/sdk/events",
        json={"events": [
            {"flag_key": "checkout", "event_type": "exposure", "variation_index": 0, "user_id": "u"}
        ]},
        headers={"x-sdk-key": "sdk-dev-key"},
    )
    assert resp.json() == {"accepted": 0, "rejected": 1}
    results = await client.get(f"/api/projects/{beta}/experiments/checkout/results")
    assert results.json()["variations"] == []


async def test_revoked_key_is_rejected(client):
    key = await new_key(client, "default")
    assert (await client.get("/sdk/config", headers={"x-sdk-key": key})).status_code == 200
    keys = (await client.get("/api/projects/default/keys")).json()
    key_id = next(k["id"] for k in keys if k["label"] == "test")
    assert (await client.delete(f"/api/projects/default/keys/{key_id}")).status_code == 200
    assert (await client.get("/sdk/config", headers={"x-sdk-key": key})).status_code == 401


async def test_key_secret_only_returned_once(client):
    created = (await client.post("/api/projects/default/keys", json={"label": "ci"})).json()
    assert created["key"].startswith("fs_")
    listed = (await client.get("/api/projects/default/keys")).json()
    assert all("key" not in k for k in listed)
    assert created["key"] not in json.dumps(listed)


async def test_flag_changes_only_notify_own_project(app, client):
    beta = await new_project(client)
    manager = app.state.sse_manager
    default_q = await manager.subscribe("project:default")
    beta_q = await manager.subscribe(f"project:{beta}")
    await client.post(f"/api/projects/{beta}/flags", json=FLAG)
    assert default_q.empty()
    assert json.loads(beta_q.get_nowait()) == {"event": "created", "key": "checkout"}


# Members


async def test_invite_pending_user_applies_on_sign_in(app, client):
    beta = await new_project(client)
    resp = await client.post(
        f"/api/projects/{beta}/members", json={"email": "New@Example.com", "role": "viewer"}
    )
    assert resp.json()["invitations"][0]["email"] == "new@example.com"
    token = await sign_in_as(app, "new@example.com")
    async with make_client(app, token) as c:
        projects = (await c.get("/api/me")).json()["projects"]
        assert [(p["id"], p["role"]) for p in projects] == [(beta, "viewer")]
    members = (await client.get(f"/api/projects/{beta}/members")).json()
    assert members["invitations"] == []
    assert len(members["members"]) == 2


async def test_last_admin_cannot_leave(client):
    beta = await new_project(client)
    me = (await client.get("/api/me")).json()["user"]["id"]
    resp = await client.put(f"/api/projects/{beta}/members/{me}", json={"role": "viewer"})
    assert resp.status_code == 400
    assert (await client.delete(f"/api/projects/{beta}/members/{me}")).status_code == 400


async def test_default_project_cannot_be_deleted(client):
    assert (await client.delete("/api/projects/default")).status_code == 400


async def test_delete_project_removes_its_data(client):
    beta = await new_project(client)
    await client.post(f"/api/projects/{beta}/flags", json=FLAG)
    key = await new_key(client, beta)
    assert (await client.delete(f"/api/projects/{beta}")).status_code == 204
    assert (await client.get("/sdk/config", headers={"x-sdk-key": key})).status_code == 401
    assert (await client.get(f"/api/projects/{beta}/flags")).status_code == 404


# Evaluate ("test a user")


async def test_evaluate_explains_rule_and_rollout(client):
    await client.post("/api/flags", json={
        **FLAG,
        "rules": [{"attribute": "plan", "operator": "equals", "value": "pro", "variation": 1}],
        "rollout": {"variation": 1, "percentage": 0},
    })
    pro_user = {"user": {"id": "u", "plan": "pro"}}
    rule = (await client.post("/api/flags/checkout/evaluate", json=pro_user)).json()
    assert rule == {**rule, "variation_index": 1, "value": True, "reason": "rule", "rule_index": 0}
    out = (await client.post("/api/flags/checkout/evaluate", json={"user": {"id": "u"}})).json()
    assert out["reason"] == "outside_rollout"
    assert out["variation_index"] == 0


# OAuth flow (GitHub, with the provider mocked)


@pytest.fixture
def github_settings(app):
    settings = Settings(
        github_client_id="cid", github_client_secret="secret", public_url="http://ui"
    )
    app.dependency_overrides[get_settings] = lambda: settings
    return settings


def mock_github(email_verified=True):
    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok"})
    )
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(200, json={"id": 42, "login": "octo", "name": "Octo Cat"})
    )
    respx.get("https://api.github.com/user/emails").mock(
        return_value=httpx.Response(
            200, json=[{"email": "octo@example.com", "primary": True, "verified": email_verified}]
        )
    )


async def start_login(c, next_path="/projects/default/flags"):
    resp = await c.get("/auth/github/login", params={"next": next_path})
    assert resp.status_code == 302
    location = urlparse(resp.headers["location"])
    assert location.netloc == "github.com"
    query = parse_qs(location.query)
    assert query["redirect_uri"] == ["http://ui/auth/github/callback"]
    return query["state"][0]


async def test_providers_lists_configured_only(anon_client, github_settings):
    body = (await anon_client.get("/auth/providers")).json()
    assert body == {"providers": [{"id": "github", "label": "GitHub"}], "dev_login": False}


@respx.mock
async def test_github_login_creates_session(anon_client, github_settings):
    mock_github()
    state = await start_login(anon_client)
    resp = await anon_client.get("/auth/github/callback", params={"code": "c", "state": state})
    assert resp.status_code == 302
    assert resp.headers["location"] == "http://ui/projects/default/flags"
    me = (await anon_client.get("/api/me")).json()
    assert me["user"]["email"] == "octo@example.com"
    assert me["identities"] == ["github"]


@respx.mock
async def test_github_login_rejects_bad_state(anon_client, github_settings):
    mock_github()
    await start_login(anon_client)
    resp = await anon_client.get("/auth/github/callback", params={"code": "c", "state": "forged"})
    assert resp.headers["location"].startswith("http://ui/login?error=")
    assert (await anon_client.get("/api/me")).status_code == 401


@respx.mock
async def test_github_login_requires_verified_email(anon_client, github_settings):
    mock_github(email_verified=False)
    state = await start_login(anon_client)
    resp = await anon_client.get("/auth/github/callback", params={"code": "c", "state": state})
    assert "verified" in resp.headers["location"]
    assert (await anon_client.get("/api/me")).status_code == 401


@respx.mock
async def test_login_next_cannot_redirect_offsite(anon_client, github_settings):
    mock_github()
    state = await start_login(anon_client, next_path="//evil.example/")
    resp = await anon_client.get("/auth/github/callback", params={"code": "c", "state": state})
    assert resp.headers["location"] == "http://ui/"


async def test_unconfigured_provider_404(anon_client):
    assert (await anon_client.get("/auth/slack/login")).status_code == 404


# Dev login


async def test_dev_login_disabled_by_default(anon_client):
    resp = await anon_client.post("/auth/dev-login", json={"email": "d@example.com"})
    assert resp.status_code == 404


async def test_dev_login_when_enabled(app, anon_client):
    app.dependency_overrides[get_settings] = lambda: Settings(dev_login=True)
    resp = await anon_client.post("/auth/dev-login", json={"email": "d@example.com"})
    assert resp.status_code == 200
    assert (await anon_client.get("/api/me")).json()["user"]["email"] == "d@example.com"
