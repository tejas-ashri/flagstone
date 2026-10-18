# Flagstone

Flagstone is a feature flag and experimentation platform for teams that need to release product changes safely, target features to specific users, and measure rollout performance. It provides a FastAPI backend for flag management, a React admin interface for operators, and a lightweight Python SDK that applications can use to fetch configuration, evaluate flags, and send exposure or conversion events.

The core workflow is simple: product or engineering teams create feature flags with variations, targeting rules, and optional percentage rollouts. Client applications initialize the SDK with an SDK key, fetch the latest flag configuration, evaluate users locally, and report analytics events back to the backend. This helps teams separate deployment from release, reduce risky all-at-once launches, and compare experiment performance across variations.

## Core Features

- Feature flag CRUD APIs for creating, updating, listing, reading, and deleting flags.
- Rule-based targeting using user attributes such as equality, containment, numeric comparison, and list membership.
- Percentage rollout support for gradual launches and controlled experiments.
- Python SDK with local evaluation, polling, optional Server-Sent Events updates, disk cache fallback, and event buffering.
- Exposure and conversion tracking for experiment result analysis.
- React admin frontend for managing flags and viewing experiment results.
- PostgreSQL-backed persistence with Alembic migrations.
- Docker Compose setup for local backend and database onboarding.

## Repository Layout

```text
flagstone/
├── alembic/
│   ├── versions/              Database migration scripts
│   ├── env.py                 Alembic migration environment
│   ├── README                 Alembic notes
│   └── script.py.mako         Migration file template
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
- Flagstone API on `http://localhost:8000`
- Default SDK key: `sdk-dev-key`

### 3. Apply database migrations

In a separate terminal, run:

```bash
alembic upgrade head
```

If running outside Docker, install the Python package first:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn backend.main:app --reload
```

### 4. Start the admin frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs through Vite and communicates with the backend API endpoints under `/api`.

### 5. Use the Python SDK in a client application

```python
from sdk.client import FlagClient

client = FlagClient(
    sdk_key="sdk-dev-key",
    base_url="http://localhost:8000",
)

user = {"id": "user-123", "plan": "pro", "country": "IN"}

if client.is_enabled("new-dashboard", user):
    print("Show the new dashboard")

client.track_conversion("new-dashboard", user)
client.close()
```

## API Overview

### Flag Management APIs

Base path: `/api/flags`

| Method | Endpoint | Responsibility |
| --- | --- | --- |
| `GET` | `/api/flags` | Lists all configured feature flags. |
| `GET` | `/api/flags/{key}` | Fetches one flag by its unique key. |
| `POST` | `/api/flags` | Creates a new feature flag with variations, rules, and rollout settings. |
| `PUT` | `/api/flags/{key}` | Updates an existing flag and broadcasts a change signal to connected SDK clients. |
| `DELETE` | `/api/flags/{key}` | Deletes a flag and broadcasts a deletion signal to connected SDK clients. |

### SDK APIs

Base path: `/sdk`

All SDK endpoints require the `x-sdk-key` request header.

| Method | Endpoint | Responsibility |
| --- | --- | --- |
| `GET` | `/sdk/config` | Returns the current flag configuration for SDK clients. |
| `GET` | `/sdk/stream` | Opens a Server-Sent Events stream for real-time flag update notifications. |
| `POST` | `/sdk/events` | Accepts batched exposure and conversion events from SDK clients. |

### Experiment Analytics APIs

Base path: `/api/experiments`

| Method | Endpoint | Responsibility |
| --- | --- | --- |
| `GET` | `/api/experiments/{key}/results` | Returns exposure counts, conversion counts, and conversion rates per variation for a flag. |

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

- The database includes an `sdk_keys` table for future revocable SDK key support.
- Event batches are capped at 1,000 records per request.

## Tech Stack

- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy AsyncIO
- Database: PostgreSQL 16, Alembic migrations
- SDK: Python, httpx, local disk cache, polling, Server-Sent Events
- Frontend: React 18, TypeScript, Vite
- Testing and Quality: pytest, pytest-asyncio, Ruff
- Runtime and DevOps: Docker, Docker Compose, Uvicorn
