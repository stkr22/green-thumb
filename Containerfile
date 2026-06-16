# Backend image. Self-contained build (no pre-built wheel needed) so the same
# Containerfile works for docker-compose, CI, and the cluster.

# Build stage: Python 3.14.4-trixie
FROM docker.io/library/python:3.14.4-trixie@sha256:8f84f00e6981bff45ce0ed100019142e13a397412bc130425f34ece42906cd48 AS build-python

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.11.8@sha256:3b7b60a81d3c57ef471703e5c83fd4aaa33abcd403596fb22ab07db85ae91347 /uv /uvx /bin/

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

# Runtime stage: Python 3.14.4-slim-trixie
FROM docker.io/library/python:3.14.4-slim-trixie@sha256:538a18f1db92b4210a0b71aca2d14c156a96dedbe8867465c8ff4dce04d2ec39

ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --no-create-home --ingroup appuser appuser

WORKDIR /app
COPY --from=build-python /app /app
# Migrations are run from this image (Job/init container), so ship them too.
COPY alembic.ini /app/
COPY alembic/ /app/alembic/

# SQLite database directory. A fresh Docker named volume mounted here inherits
# this ownership, so the non-root process can create the database file. On
# Kubernetes the PVC is made writable via the pod's fsGroup instead.
RUN mkdir -p /data && chown appuser:appuser /data
VOLUME ["/data"]

ENV PATH="/app/.venv/bin:$PATH"
USER appuser

EXPOSE 8000
CMD ["uvicorn", "greenthumb.main:app", "--host", "0.0.0.0", "--port", "8000"]
