# Application image: builds the SPA and the Python backend, then ships one
# runtime that serves both (FastAPI serves the static SPA at /). Self-contained
# so the same Containerfile works for CI and the cluster.

# Frontend build stage: compile the React SPA to static assets.
FROM docker.io/library/node:24-alpine AS build-frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci
COPY frontend/ ./
# Same-origin deployment: empty API base so the SPA calls /api and /auth on its
# own origin (now served by the backend itself).
ENV VITE_API_BASE_URL=""
RUN npm run build

# Build stage: Python 3.14.7-trixie
FROM docker.io/library/python:3.14.7-trixie@sha256:20f4b272cb5d0f462c84645f8127d82e6fcfdc4006f4dd7f8859a5be4d5ef7a5 AS build-python

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Install uv. Must satisfy `required-version` in pyproject.toml ([tool.uv]),
# otherwise `uv sync` below refuses to run.
COPY --from=ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 /uv /uvx /bin/

WORKDIR /app

# Dependency layer first so source edits don't bust the cache.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache \
    uv sync --locked --no-install-project --no-dev

# README.md and LICENSE are required at build time: pyproject.toml declares
# them via `readme` and `license-files`, so the uv_build backend reads both
# when building the package below.
COPY src/ src/
COPY README.md LICENSE ./
RUN --mount=type=cache,target=/root/.cache \
    uv sync --locked --no-dev

# Runtime stage: Python 3.14.7-slim-trixie
FROM docker.io/library/python:3.14.7-slim-trixie@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4

ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --no-create-home --ingroup appuser appuser

WORKDIR /app
COPY --from=build-python /app /app
# Migrations are run from this image (Job/init container), so ship them too.
COPY alembic.ini /app/
COPY alembic/ /app/alembic/

# Built SPA, served by FastAPI at / (see main.py / STATIC_DIR).
COPY --from=build-frontend /frontend/dist /app/static
ENV STATIC_DIR=/app/static

# SQLite database directory. A fresh Docker named volume mounted here inherits
# this ownership, so the non-root process can create the database file. On
# Kubernetes the PVC is made writable via the pod's fsGroup instead.
RUN mkdir -p /data && chown appuser:appuser /data
VOLUME ["/data"]

ENV PATH="/app/.venv/bin:$PATH"
USER appuser

EXPOSE 8000
CMD ["uvicorn", "greenthumb.main:app", "--host", "0.0.0.0", "--port", "8000"]
