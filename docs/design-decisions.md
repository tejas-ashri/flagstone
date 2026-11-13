# Design decisions

The main choices behind Flagstone, what they buy, and what they cost.

## Evaluation runs in the SDK

**Decision.** Applications download the whole flag configuration and evaluate locally, rather than asking the server "is this on for user X?" each time.

**Why.**
- A flag check is microseconds and needs no network, so you can check flags in hot paths.
- If Flagstone is down, applications keep working with the last configuration they had, or the disk cache at startup.
- Server load depends on the number of *applications*, not the number of flag checks.

**Cost.**
- Targeting rules and their values (for example lists of customer ids) are visible to any holder of the project's SDK key. SDK keys belong in server-side applications, not in browsers or mobile apps.
- The evaluator and bucketing exist twice, in `sdk/` and `backend/services/`, so the SDK can be installed without the backend's dependencies. Tests assert the two agree; any change must be made to both.

## Bucketing by hash, not stored assignments

**Decision.** A user's rollout bucket is `md5("{flag_key}:{user_id}") mod 100`, computed on the fly.

**Why.** No storage, no coordination between SDK instances, and the same answer everywhere, forever. Raising a percentage only adds users. Including the flag key keeps different flags' rollouts independent.

**Cost.** You can't hand-pick who is in the rollout percentage; use a rule for that. And the hash function can never change without reshuffling every running rollout.

## SSE as a change signal, not a data channel

**Decision.** The stream sends `{"event": "updated", "key": "…"}`, and clients refetch `/sdk/config`.

**Why.** There is one source of truth and one code path for loading configuration. A client that missed messages while disconnected is fully correct after its next fetch. The stream carries no flag contents.

**Cost.** One extra request per change per client. Polling remains the default because it works through every proxy and load balancer.

## SSE fan-out is in-process

**Decision.** `SSEConnectionManager` keeps subscriber queues in memory.

**Why.** No extra infrastructure for a single-instance deployment.

**Cost.** With **several API instances**, a change saved on instance A only reaches SDKs streaming from A. Polling clients are unaffected. To scale out with SSE, replace the manager's `broadcast` with Postgres `LISTEN/NOTIFY` or Redis pub/sub. Its interface (`subscribe` / `unsubscribe` / `broadcast`) was kept small for that reason.

## Projects as the isolation boundary

**Decision.** Flags, events, SDK keys and members all hang off a project, and the project is resolved on the server from the URL (people) or the SDK key (applications).

**Why.** The requirement was that an admin's access and an SDK key's access match. Tying both to the same project id, and making the SDK key *determine* the project rather than letting the request choose it, makes that structural rather than a check someone might forget.

**Cost.** Flag keys are unique only per project, which made the primary key composite `(project_id, key)` and forced a migration of existing data (`005`).

## Backwards compatibility through a Default project

**Decision.** Existing flags, events and keys moved into a project called `default`; the original `/api/flags` and `/api/experiments` paths still work and act on it; the `SDK_KEY` setting is seeded as one of its keys.

**Why.** Nothing that worked before had to change: existing SDK deployments, scripts and tests keep working. The 52 original tests pass with only a test-fixture change, which signs the test client in.

**Cost.** The Default project is special: it can't be deleted, and migration `005` can only be downgraded when no other project holds flags or keys.

## OAuth only, no passwords

**Decision.** People sign in with GitHub, Google or Slack; Flagstone stores no passwords.

**Why.** No password storage, reset flows or MFA to build. Providers already do this well, and teams already have these accounts.

**Choices within it.**
- **Authorization code flow, handled by the backend.** The client secret never reaches the browser.
- **Hand-written provider code over `httpx`** instead of an OAuth library: about 150 lines for three providers, no new dependency, and every step is visible.
- **Identity via `userinfo`** for Google and Slack, rather than validating the `id_token` JWT. This avoids a JWT library and key-rotation handling, at the price of one extra HTTP call per sign-in.
- **Accounts linked by verified email**, so the same person can use any provider. Unverified emails are refused outright, because email is also what invitations and `ADMIN_EMAILS` trust.

## Server-side sessions, not JWTs

**Decision.** The cookie holds a random token; the database holds its hash.

**Why.** Sign-out and revocation take effect immediately. JWTs can't be revoked before they expire without building a deny-list, which recreates server state anyway.

**Cost.** One primary-key lookup per admin request. That's negligible for an admin UI.

## CSRF: SameSite cookie plus a custom header

**Decision.** No CSRF tokens; instead `SameSite=Lax` plus a required `X-Requested-With: flagstone` header on writes.

**Why.** Equivalent protection for a same-origin JSON API, with nothing to generate, store or embed in pages.

**Cost.** API scripts using a session cookie must send the header. It's documented, and the UI does it automatically.

## Hashing secrets with SHA-256

**Decision.** SDK keys and session tokens are stored as plain SHA-256.

**Why.** Both are long random values (192 and 256 bits), so a slow password hash adds nothing; brute force is already infeasible. A deterministic hash allows a direct lookup by primary key on every request.

## Targeting stored as JSON columns

**Decision.** `variations`, `rules` and `rollout` are JSON on the flag row.

**Why.** A flag is always read and written as a whole, by the API and by the SDK. Normalised tables would add joins and multi-row transactions for no query that needs them.

**Cost.** The database doesn't validate the structure; Pydantic schemas do, on the way in. Cross-field checks, such as a rule pointing at a variation index that exists, are currently done only by the UI.

## Raw counts for experiment results

**Decision.** Results are exposure and conversion **event counts** per variation, with no statistics.

**Why.** Simple, fast, and transparent about what was measured.

**Cost.** No per-user deduplication and no confidence intervals. Treat small differences on small samples as noise. A significance test and unique-user counts are the natural next step.

## Known limitations

| Limitation | Impact | Possible fix |
| --- | --- | --- |
| SSE fan-out is in memory | Multi-instance deployments only notify SSE clients on the instance that saved | Postgres `LISTEN/NOTIFY` or Redis pub/sub |
| `NullPool` database engine | A new connection per request; fine at low volume, wasteful at scale | Use the default pool, or PgBouncer |
| Server doesn't validate variation indexes or rollout range | An API client can save a flag the SDK can't evaluate (the UI prevents it) | Cross-field validators on `FlagCreate` / `FlagUpdate` |
| SDK event delivery is best-effort | A failed flush drops that batch | Retry with a bounded buffer |
| `track_conversion` re-evaluates the flag | If targeting changed in between, a conversion can be credited to another variation | Remember the variation served per user in the SDK |
| No audit log | No record of who changed which flag | An `audit_events` table written by `flag_service` |
| SDK keys are server-side only | Can't be safely used from browsers or mobile apps | Client-side keys with server-evaluated, per-user responses |
