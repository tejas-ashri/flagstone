# Backend services

`backend/services/` holds the business logic. Routers call services; services talk to the database through SQLAlchemy sessions passed in by the caller. Services never read the HTTP request themselves, which keeps them testable without a web server.

| Module | Role in one line |
| --- | --- |
| [`flag_service`](#flag_service) | Create, read, update and delete flags within a project |
| [`evaluator`](#evaluator) | Decide which variation a user gets |
| [`bucketing`](#bucketing) | Deterministically map a user to a rollout bucket 0–99 |
| [`explain`](#explain) | Say *why* a user gets a variation (for "Test a user") |
| [`analytics_service`](#analytics_service) | Store events and compute experiment results |
| [`sdk_key_service`](#sdk_key_service) | Create, look up and revoke per-project SDK keys |
| [`auth_service`](#auth_service) | Sign people in, link identities, manage sessions |
| [`oauth`](#oauth) | Talk to GitHub, Google and Slack during sign-in |
| [`project_service`](#project_service) | Projects, members, invitations and roles |
| [`bootstrap`](#bootstrap) | Prepare the Default project and seed `SDK_KEY` at startup |

Services raise `fastapi.HTTPException` for "not found" and "conflict" cases, so routers can stay one-liners. This couples services slightly to FastAPI, accepted here for simplicity.

---

## `flag_service`

**File:** `backend/services/flag_service.py` · **Used by:** `routers/flags.py`, `routers/analytics.py`, `routers/sdk.py`

**Role.** The only code that writes to the `flags` table. Every function takes a `project_id`, so a flag can never be read or changed outside the project the caller was authorised for.

| Function | Does |
| --- | --- |
| `list_flags(db, project_id)` | All flags of a project, sorted by key, as `FlagResponse` |
| `get_flag(db, project_id, key)` | One flag, or 404 |
| `flag_keys(db, project_id)` | The set of keys; used to filter incoming SDK events |
| `create_flag(db, project_id, data)` | Insert, or 409 if the key already exists *in this project* |
| `update_flag(db, project_id, key, data)` | Partial update; see below |
| `delete_flag(db, project_id, key)` | Delete; events go with it via `ON DELETE CASCADE` |

**Partial updates.** `update_flag` uses Pydantic's `model_fields_set` to tell "field not sent" from "field sent as `null`". This is what lets `{"rollout": null}` *clear* a rollout while `{"enabled": false}` leaves the rollout alone. It's how the UI's on/off switch avoids overwriting targeting edits.

**Significance.** Flags are the product. Keeping every write in one module means the project-scoping guarantee is enforced in one place.

---

## `evaluator`

**File:** `backend/services/evaluator.py` (mirrors `sdk/evaluator.py`) · **Used by:** `explain`, tests

**Role.** The pure function `evaluate(flag: dict, user: dict) -> int`, which returns the variation index. Order: disabled → default; first matching rule → its variation; rollout → `rollout.variation` if the user's bucket is below the percentage; otherwise the default. `_match_rule` implements the five operators.

**Significance.** This is the core decision of the whole system. In production the SDK copy does the evaluating; this server copy powers the admin "Test a user" tool, so admins see exactly what applications compute. `tests/test_evaluator.py::test_backend_and_sdk_evaluate_match` guards against the copies drifting apart.

**Why it's duplicated rather than shared:** the SDK is meant to be installed into applications without pulling in the backend (FastAPI, SQLAlchemy…). See [design decisions](design-decisions.md#evaluation-runs-in-the-sdk).

---

## `bucketing`

**File:** `backend/services/bucketing.py` (mirrors `sdk/bucketing.py`) · **Used by:** `evaluator`, `explain`

**Role.** `bucket(flag_key, user_id)` hashes `"{flag_key}:{user_id}"` with MD5 and returns the first 32 bits modulo 100. `in_rollout(..., percentage)` is `bucket < percentage`.

**Significance.** Bucketing makes percentage rollouts **stable** (a user doesn't flip between variations), **monotonic** (raising the percentage only adds users) and **independent per flag**. Changing this function would reshuffle every user in every running rollout, so treat it as frozen. `tests/test_bucketing.py` pins backend and SDK agreement.

---

## `explain`

**File:** `backend/services/explain.py` · **Used by:** `POST /api/projects/{id}/flags/{key}/evaluate`

**Role.** `explain(flag, user)` returns the variation plus a reason: `disabled`, `rule` (with `rule_index`), `rollout` / `outside_rollout` (with `bucket` and `rollout_percentage`), or `default`.

**How it stays honest.** The variation always comes from calling `evaluator.evaluate`; `explain` only reconstructs the reason alongside it, using the same `_match_rule` and `bucket`. Even if the explanation logic had a bug, the *answer* shown to the admin would still be the real one.

**Significance.** Targeting with several rules and a rollout is hard to reason about. "Why does this customer see the old checkout?" becomes a 5-second check instead of a debugging session. The router also turns configuration errors (for example `in` with a non-list value) into a readable 422 instead of letting them surface later as SDK crashes.

---

## `analytics_service`

**File:** `backend/services/analytics_service.py` · **Used by:** `routers/sdk.py` (write), `routers/analytics.py` (read)

| Function | Does |
| --- | --- |
| `insert_events(db, project_id, events)` | Bulk-insert a batch, tagging every event with the SDK key's project. Uses the client timestamp if present, otherwise the time received. |
| `get_experiment_results(db, project_id, flag_key)` | One `GROUP BY variation_index` query with `COUNT(*) FILTER (…)` for exposures and conversions; computes the conversion rate in Python. |

**Significance.** This is the "experimentation" half of the platform. It's deliberately simple: raw counts, no deduplication by user and no statistics. See [How it works § 6](how-it-works.md#6-events-and-experiment-results) for how to read the numbers. The `(project_id, flag_key, event_type, received_at)` index keeps the query fast as events accumulate.

The router filters events for unknown flags *before* calling `insert_events` (via `flag_service.flag_keys`), so one stale flag key in a batch can't make the whole batch fail on the composite foreign key.

---

## `sdk_key_service`

**File:** `backend/services/sdk_key_service.py` · **Used by:** `routers/projects.py` (manage), `routers/sdk.py` (authenticate), `bootstrap`

| Function | Does |
| --- | --- |
| `create_key(db, project_id, label)` | Generates `fs_` + 32 random URL-safe characters, stores its SHA-256 hash and a 10-character display prefix, and returns the raw key **once** |
| `list_keys(db, project_id)` | Metadata only; raw keys are never retrievable |
| `revoke_key(db, project_id, key_hash)` | Sets `revoked_at`. Only for keys of the same project; anything else is a 404 |
| `resolve_key(db, raw)` | Hash → row; `None` if unknown or revoked. Updates `last_used_at` at most every 5 minutes |
| `hash_key(raw)` | SHA-256 hex |

**Significance.** This is the boundary that makes "an SDK key only sees its own project" true. `routers/sdk.py::_verify_sdk_key` calls `resolve_key` and hands the **project id**, not the key, to every SDK endpoint, so a key physically can't name another project.

**Why plain SHA-256 and not bcrypt:** keys are 192 bits of randomness, so brute-forcing a hash is infeasible without a slow hash. A deterministic hash also allows a direct primary-key lookup on every SDK request; a salted slow hash would need a scan.

**`last_used_at` throttling:** SDKs poll every 30 s. Writing a timestamp on every poll would turn a read-only endpoint into a write-heavy one, so it's updated at most every 5 minutes. That's enough to answer "is this key still in use?" before revoking it.

---

## `auth_service`

**File:** `backend/services/auth_service.py` · **Used by:** `routers/auth.py`, `deps.py`

| Function | Does |
| --- | --- |
| `sign_in(db, profile, settings)` | Turns a verified provider `Profile` into a `User`, then applies pending access (see below) |
| `create_session(db, user_id, settings)` | Random 256-bit token; stores its hash with an expiry (7 days by default); returns the raw token for the cookie |
| `user_for_session(db, token)` | Token → user; deletes and rejects expired sessions |
| `delete_session(db, token)` | Sign-out |
| `identities_for(db, user_id)` | Which providers a user has signed in with |

**What `sign_in` does, in order:**
1. **Refuses unverified emails.** Email is the identity everyone else relies on: invitations, `ADMIN_EMAILS` and account linking.
2. Finds the user by `(provider, provider_user_id)`; failing that, by email; failing that, creates one. A person who signs in with GitHub today and Google tomorrow, with the same verified email, gets **one** account.
3. Refreshes name and avatar from the provider.
4. If the email is in `ADMIN_EMAILS`, grants admin on the Default project.
5. Converts any **invitations** for that email into memberships and deletes them.

**Significance.** Everything people can do is anchored here. Keeping provider-specific code out (that's `oauth`) means adding a provider never touches account logic.

---

## `oauth`

**File:** `backend/services/oauth.py` · **Used by:** `routers/auth.py`

**Role.** Speaks the authorization-code flow to each provider and normalises the result into a `Profile(provider, provider_user_id, email, email_verified, name, avatar_url)`.

| Provider | Token endpoint | Profile source | Verified email from |
| --- | --- | --- | --- |
| GitHub | `github.com/login/oauth/access_token` | `api.github.com/user` | `api.github.com/user/emails`, the primary verified address |
| Google | `oauth2.googleapis.com/token` | OpenID `userinfo` | `email_verified` claim |
| Slack | `slack.com/api/openid.connect.token` | `openid.connect.userInfo` | `email_verified` claim |

Key pieces:
- `PROVIDERS` is a registry of the provider name, label, authorize URL and scopes. A provider counts as *configured*, and appears on the login page, only when both its client ID and secret are set.
- `authorize_url()` builds the redirect to the provider, including the `state` value.
- `fetch_profile()` exchanges the code and reads the profile. Every failure becomes `OAuthError` with a human-readable message, shown on the login page.
- Slack reports errors as HTTP 200 with `{"ok": false}`, which is handled explicitly.

**Design note.** For Google and Slack the identity is read from the `userinfo` endpoint over TLS using the access token, rather than by verifying the `id_token` JWT locally. This avoids a JWT/JWKS dependency and key rotation handling, at the cost of one extra HTTP call per sign-in.

**Significance.** It isolates everything provider-specific. Adding, say, Microsoft means one new `Provider` entry and one exchange function.

---

## `project_service`

**File:** `backend/services/project_service.py` · **Used by:** `routers/projects.py`, `routers/auth.py`

| Function | Does |
| --- | --- |
| `projects_for(db, user_id)` | The user's projects with role, flag count and member count, in one query |
| `create_project(db, name, owner)` | New project with a readable id (`checkout-web-3f9a1c`); the creator becomes admin |
| `rename_project` / `get_project` | — |
| `delete_project(db, project_id)` | Deletes events, flags, keys, invitations and memberships explicitly, then the project. The Default project is protected. |
| `list_members` | Members (with user details) and pending invitations |
| `invite(db, project_id, email, role, invited_by)` | Existing user → membership straight away; unknown email → invitation applied at their first sign-in |
| `set_role` / `remove_member` | Refuse to remove or demote the **last admin** |
| `cancel_invite` | — |

**Significance.** This module defines who can reach which project, and therefore which flags. Two guards prevent common lock-outs: a project can never lose its last admin, and the Default project, which the legacy API paths depend on, can't be deleted.

Deletion is explicit rather than relying only on `ON DELETE CASCADE`, so it behaves the same on SQLite (tests) and PostgreSQL.

---

## `bootstrap`

**File:** `backend/services/bootstrap.py` · **Used by:** `main.py` lifespan, test fixtures

**Role.** `ensure_defaults()` runs once at startup:
1. Creates the Default project if it's missing. Migration 004 also creates it; this covers databases built from the ORM, such as tests.
2. Inserts the configured `SDK_KEY`, hashed, as a Default-project key if that hash isn't there yet.

It **only inserts and never updates**, so revoking the seeded key in the UI survives restarts. If the database isn't migrated, startup fails with a message telling you to run `alembic upgrade head`.

**Significance.** This is the backwards-compatibility bridge: applications configured with `sdk-dev-key` before projects existed keep working without changes.

---

## Other backend modules

| Module | Role |
| --- | --- |
| `main.py` | `create_app()` wires routers. Flags and analytics routers are mounted twice: under `/api/projects/{project_id}` and, for backwards compatibility, under `/api` (acting on the Default project, hidden from the OpenAPI docs). `lifespan` creates the engine and SSE manager and runs `bootstrap`. |
| `config.py` | `Settings` (pydantic-settings) reads environment variables and `.env`. Cached by `get_settings()`, so a restart is needed after changes. |
| `deps.py` | Request-scoped dependencies: `get_db`; `get_current_user` (session cookie → user, plus the CSRF header check on writes); `project_viewer` / `project_admin` (resolves the project from the path, checks membership, returns `ProjectAccess`). Non-members get **404**, not 403, so project ids can't be probed. |
| `db/session.py` | Engine and session factory. Uses `NullPool`: a new database connection per session (see [design decisions](design-decisions.md#known-limitations)). |
| `db/sse_manager.py` | `SSEConnectionManager`: an in-memory map from channel to subscriber queues. `broadcast` never blocks; a full queue (100 messages) drops the message for that slow subscriber. |
| `models/orm.py` | SQLAlchemy models for all tables. `DEFAULT_PROJECT_ID = "default"`. |
| `schemas/flag.py` | `FlagCreate`, `FlagUpdate` (all optional, for partial updates), `FlagResponse`, `FlagRule`, `FlagRollout`. |
| `schemas/event.py` | `EventRecord`, `EventBatch` (max 1,000), `ExperimentResults`. |
| `schemas/project.py` | Projects, keys, members, invitations, `/api/me`, evaluate request/response, dev login. |
| `routers/flags.py` | Flag CRUD and `evaluate`; broadcasts `created` / `updated` / `deleted` to `project:{id}`. |
| `routers/analytics.py` | Experiment results. |
| `routers/sdk.py` | `/sdk/config`, `/sdk/stream`, `/sdk/events`; authenticates by SDK key and works only on that key's project. |
| `routers/projects.py` | Projects, SDK keys and members endpoints. |
| `routers/auth.py` | OAuth login/callback, dev login, logout, `/api/me`, and the cookie handling. |
