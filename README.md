# Flagstone

Flagstone is a feature flag and experimentation platform for teams that need to release product changes safely, target features to specific users, and measure rollout performance. It provides a FastAPI backend for flag management, a React admin interface for operators, and a lightweight Python SDK that applications can use to fetch configuration, evaluate flags, and send exposure or conversion events.

The core workflow is simple: product or engineering teams create feature flags with variations, targeting rules, and optional percentage rollouts. Client applications initialize the SDK with an SDK key, fetch the latest flag configuration, evaluate users locally, and report analytics events back to the backend. This helps teams separate deployment from release, reduce risky all-at-once launches, and compare experiment performance across variations.

## Core Features

- Feature flag CRUD APIs for creating, updating, listing, reading, and deleting flags.
- Rule-based targeting using user attributes such as equality, containment, numeric comparison, and list membership.
- Percentage rollout support for gradual launches and controlled experiments.
- Python SDK with local evaluation, polling, optional Server-Sent Events updates, disk cache fallback, and event buffering.
- Exposure and conversion tracking for experiment result analysis.
- Projects, each with its own flags, SDK keys and members. An SDK key only sees its own project.
- Sign-in with GitHub, Google or Slack, with admin and viewer roles per project.
- Multi-page React admin UI: projects, flags, targeting editor, "test a user", results, SDK keys and members.
- PostgreSQL-backed persistence with Alembic migrations.
- Docker Compose setup for local backend and database onboarding.

## Documentation

In-depth docs live in [`docs/`](docs/README.md): [architecture](docs/architecture.md), [how it works](docs/how-it-works.md), [backend services](docs/backend-services.md), [authentication](docs/authentication.md), [frontend](docs/frontend.md) and [design decisions](docs/design-decisions.md).

## Repository Layout

```text
flagstone/
├── alembic/
│   ├── versions/              Database migration scripts
│   ├── env.py                 Alembic migration environment
│   ├── README                 Alembic notes
│   └── script.py.mako         Migration file template
├── docs/                      Architecture, design decisions and service-by-service docs
├── backend/
│   ├── db/                    Async database session and SSE connection management
│   ├── models/                SQLAlchemy ORM models
│   ├── routers/               FastAPI route groups for flags, SDK, and analytics
│   ├── schemas/               Pydantic request and response models
│   ├── services/              Core business logic for flags, bucketing, evaluation, and analytics
│   ├── config.py              Environment-based application settings
│   ├── deps.py                FastAPI dependency helpers
│   └── main.py                Application factory and router registration
├── frontend/
│   ├── public/                Static frontend assets
│   ├── src/
│   │   ├── api/               Frontend API clients
│   │   ├── assets/            Frontend assets
│   │   ├── components/        Reusable React components
│   │   ├── pages/             Page-level React views
│   │   ├── types/             TypeScript domain types
│   │   ├── App.tsx            Main React application shell
│   │   └── main.tsx           React entry point
│   ├── package.json           Frontend scripts and dependencies
│   ├── vite.config.ts         Vite configuration
│   └── tsconfig*.json         TypeScript configuration files
├── sdk/
│   ├── bucketing.py           Deterministic rollout bucketing logic
│   ├── client.py              Python SDK client
│   ├── disk_cache.py          Local SDK cache support
│   ├── evaluator.py           Flag evaluation logic
│   ├── poller.py              Periodic config refresh helper
│   └── stream_listener.py     Server-Sent Events listener
├── tests/                     Backend, SDK, analytics, SSE, and evaluator tests
├── alembic.ini                Alembic configuration
├── docker-compose.yml         Local API and PostgreSQL services
├── Dockerfile                 Backend container image definition
├── pyproject.toml             Python package, dependencies, lint, and test settings
└── README.md                  Project documentation
```

## Onboarding Process

### Prerequisites

- Python 3.12 or newer
- Node.js and npm for the admin frontend
- Docker and Docker Compose for the recommended local database setup

### 1. Clone and enter the repository

```bash
git clone <repository-url>
cd flagstone
```

### 2. Start the backend and database

The fastest local path is Docker Compose:

```bash
docker compose up --build
```

This starts:

- PostgreSQL on `localhost:5432`
- Flagstone API on `http://localhost:8000`, after applying migrations
- Default SDK key: `sdk-dev-key`
- Development sign-in enabled, with `admin@example.com` as admin of the Default project

### 3. Running without Docker (optional)

Install the Python package, apply migrations, then start the API. Migrations must run first, because the API seeds the Default project's SDK key on startup.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then set DEV_LOGIN=true or OAuth credentials
alembic upgrade head
uvicorn backend.main:app --reload
```

### 4. Start the admin frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api`, `/auth` and `/sdk` to the backend, so the UI and API share an origin and the session cookie. With Docker Compose's defaults, use the development sign-in with `admin@example.com`.

In production, serve the built frontend (`npm run build`, output in `frontend/dist`) and the API behind one domain, routing `/api`, `/auth` and `/sdk` to the backend.

### 5. Use the Python SDK in a client application

```python
from sdk.client import FlagClient

client = FlagClient(
    sdk_key="sdk-dev-key",  # or a key from the project's "SDK keys" page
    base_url="http://localhost:8000",
)

user = {"id": "user-123", "plan": "pro", "country": "IN"}

if client.is_enabled("new-dashboard", user):
    print("Show the new dashboard")

client.track_conversion("new-dashboard", user)
client.close()
```

## Authentication and Projects

Flags, experiment events and SDK keys belong to a **project**. The two kinds of access are checked separately:

- **People** sign in with GitHub, Google or Slack and see only the projects they're members of. An **admin** can change flags, SDK keys, members and settings; a **viewer** can see flags and results.
- **Applications** authenticate with an **SDK key**. A key is tied to one project: `/sdk/config` returns only that project's flags, `/sdk/stream` only signals that project's changes, and `/sdk/events` drops events for flags outside it.

So the admin configuring a flag and the SDK key that serves it always resolve to the same project; one project's key can never read or report on another project's flags.

Existing data lives in the **Default** project. The `SDK_KEY` setting is seeded as one of its keys, so existing SDK clients keep working. SDK keys are stored only as SHA-256 hashes, and the full key is shown once at creation.

### Getting the first admin

Users who sign in with an email listed in `ADMIN_EMAILS` become admins of the Default project. Anyone signed in can create a new project, and becomes its admin. Admins invite others by email on the Members page; the invitation applies the next time that person signs in with any provider that reports the email as verified.

### Configuring sign-in providers

Only providers with both settings configured appear on the login page. Register an OAuth app with each provider, using the callback URL `{PUBLIC_URL}/auth/{provider}/callback`. With the default `PUBLIC_URL`, that is `http://localhost:5173/auth/github/callback`.

| Provider | Where to register | Settings | Notes |
| --- | --- | --- | --- |
| GitHub | Settings → Developer settings → OAuth Apps | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | Requests `read:user user:email` |
| Google | Google Cloud Console → APIs & Services → Credentials → OAuth client ID (Web) | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Scopes `openid email profile` |
| Slack | api.slack.com/apps → OAuth & Permissions → Redirect URLs | `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` | Uses Sign in with Slack (OpenID Connect) |

Sign-in requires a verified email address. Accounts are matched by email, so one person can use any configured provider.

For local work without registering apps, set `DEV_LOGIN=true` to get a passwordless email sign-in. Never enable it where others can reach the server.

### Security notes

- Sessions are random tokens in an `httpOnly`, `SameSite=Lax` cookie, stored hashed server-side and deleted on sign-out. Set `COOKIE_SECURE=true` when serving over HTTPS.
- State-changing admin requests must carry `X-Requested-With: flagstone`, which blocks cross-site form posts. The UI sends it automatically.

## API Overview

### Admin APIs

Every admin endpoint requires a signed-in session. Writes need the admin role; reads work for viewers too.

Base path: `/api/projects/{project_id}`

| Method | Endpoint | Responsibility |
| --- | --- | --- |
| `GET` | `/flags` | Lists the project's flags. |
| `GET` | `/flags/{key}` | Fetches one flag. |
| `POST` | `/flags` | Creates a flag (admin). |
| `PUT` | `/flags/{key}` | Updates a flag and signals the project's connected SDK clients (admin). |
| `DELETE` | `/flags/{key}` | Deletes a flag and signals the project's connected SDK clients (admin). |
| `POST` | `/flags/{key}/evaluate` | Evaluates the saved flag for a given user and explains the result. |
| `GET` | `/experiments/{key}/results` | Exposures, conversions and conversion rate per variation. |
| `GET`, `POST` | `/keys` | Lists or creates SDK keys (create: admin; the full key is returned only here). |
| `DELETE` | `/keys/{id}` | Revokes an SDK key (admin). |
| `GET`, `POST` | `/members` | Lists members and pending invitations, or invites by email (admin). |
| `PUT`, `DELETE` | `/members/{user_id}` | Changes a role or removes a member (admin). A project always keeps one admin. |
| `DELETE` | `/invitations/{email}` | Cancels an invitation (admin). |

| Method | Endpoint | Responsibility |
| --- | --- | --- |
| `GET`, `POST` | `/api/projects` | Lists your projects, or creates one. |
| `GET`, `PUT`, `DELETE` | `/api/projects/{project_id}` | Reads, renames or deletes a project (the Default project can't be deleted). |
| `GET` | `/api/me` | The signed-in user, their sign-in methods and projects. |

The original paths `/api/flags…` and `/api/experiments…` still work, and act on the Default project with the same permission checks.

### Auth endpoints

| Method | Endpoint | Responsibility |
| --- | --- | --- |
| `GET` | `/auth/providers` | Configured sign-in providers, and whether development sign-in is on. |
| `GET` | `/auth/{provider}/login?next=/path` | Starts OAuth sign-in. |
| `GET` | `/auth/{provider}/callback` | OAuth redirect target; creates the session. |
| `POST` | `/auth/dev-login` | Passwordless sign-in when `DEV_LOGIN=true`. |
| `POST` | `/auth/logout` | Ends the session. |

### SDK APIs

Base path: `/sdk`

All SDK endpoints require the `x-sdk-key` request header and act only on that key's project.

| Method | Endpoint | Responsibility |
| --- | --- | --- |
| `GET` | `/sdk/config` | Returns the project's current flag configuration. |
| `GET` | `/sdk/stream` | Opens a Server-Sent Events stream of the project's flag changes. |
| `POST` | `/sdk/events` | Accepts batched exposure and conversion events. Returns `accepted` and `rejected` counts; events for flags outside the project are rejected. |

## Flag Model

A flag contains:

- `key`: unique flag identifier used by clients.
- `enabled`: controls whether the flag is active.
- `variations`: possible returned values, commonly `[false, true]`.
- `default_variation`: fallback variation index.
- `rules`: ordered targeting rules based on user attributes.
- `rollout`: optional percentage rollout configuration.
- `updated_at`: timestamp for the latest flag update.

## Development Commands

```bash
# Run tests
pytest

# Run linting
ruff check .

# Run backend locally
uvicorn backend.main:app --reload

# Run frontend locally
cd frontend && npm run dev
```

## Notes

- Event batches are capped at 1,000 records per request.
- Changing `SDK_KEY` adds a new Default-project key on the next start; the previous one stays active until revoked in the UI.
- Migration `005` downgrades only when no flags or keys exist outside the Default project, since flag keys are unique only per project.

## Tech Stack

- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy AsyncIO, OAuth 2.0 / OpenID Connect
- Database: PostgreSQL 16, Alembic migrations
- SDK: Python, httpx, local disk cache, polling, Server-Sent Events
- Frontend: React 18, React Router 6, TypeScript, Vite
- Testing and Quality: pytest, pytest-asyncio, Ruff
- Runtime and DevOps: Docker, Docker Compose, Uvicorn
