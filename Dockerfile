# Production image: builds the admin UI, installs the backend into a virtualenv,
# and ships only the runtime pieces in a slim final stage.

# --- Stage 1: build the React admin UI --------------------------------------
FROM node:22-alpine AS ui
WORKDIR /ui
# Install dependencies first so this layer is cached until the lockfile changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: install Python dependencies into a virtualenv -----------------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build
# Dependencies only, read from pyproject.toml, so this layer is cached until
# they change rather than on every source edit.
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
    && pip install -r requirements.txt
# The backend itself, as a regular (non-editable) install. The SDK isn't needed
# by the server, so it isn't copied. pip is removed afterwards: the runtime
# never installs anything.
COPY backend/ backend/
RUN pip install --no-deps . \
    && pip uninstall -y pip \
    && find /opt/venv -name '__pycache__' -prune -exec rm -rf {} +

# --- Stage 3: runtime --------------------------------------------------------
FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd --system --no-create-home --uid 10001 flagstone
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic/ alembic/
COPY --from=ui /ui/dist frontend/dist
USER flagstone
EXPOSE 8000
# Migrations run before the API starts, because the API seeds the Default
# project's SDK key on startup. Run a single instance: SSE fan-out is in memory.
# PORT is set by hosts such as Render; proxy headers give the real client
# scheme and IP behind their load balancer.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
