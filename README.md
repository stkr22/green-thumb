# Green Thumb

[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-orange.json)](https://github.com/copier-org/copier)
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json)](https://github.com/charliermarsh/ruff)
[![Checked with ty](https://img.shields.io/badge/types-ty-261230.svg)](https://github.com/astral-sh/ty)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

A self-hosted plant care tracker for your homelab: log watering, fertilising
and repotting, get push reminders (via [ntfy](https://ntfy.sh)) when care is
due, and keep photos of your plants — all stored in a single SQLite database,
with SSO login through [Zitadel](https://zitadel.com).

## Features

- **Plants** with species, scientific name, location, tags, notes, and photos
- **Locations** (rooms / areas) with plant counts
- **Care logging** — watering, fertilising, repotting, or custom events (backdatable)
- **Reminders** — get notified when a plant hasn't had a care event within N days
- **Dashboard** — overdue and upcoming care at a glance
- **Calendar** — monthly view of upcoming care
- **Photos** — gallery per plant, with a selectable cover photo
- **Push notifications** via ntfy, with a per-user topic override
- **Optional species lookup** via FloraCodex (autocomplete when adding a plant)
- **SSO login** through Zitadel (OIDC); no passwords stored by the app

> **Single shared household instance.** Every signed-in user sees and can edit
> **all** plants, locations, logs and reminders — there is no per-user data
> separation. Access is controlled entirely by who you allow into the Zitadel
> application. See [administration.md](docs/administration.md#user-management).

## Tech stack

- **Backend:** FastAPI + SQLModel (async, aiosqlite), Alembic migrations, Python 3.14 — `src/greenthumb/`
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS 4 + TanStack Query 5 — `frontend/`
- **Database:** SQLite (single file)
- **Deployment:** Helm chart (`charts/green-thumb/`, published as an OCI artifact) synced by ArgoCD; docker-compose for local dev
- **Interactive API docs:** Swagger UI at `/docs` on a running backend

## Quick start (local development)

```bash
cp .env.local.example .env.local   # fill in OIDC credentials
docker compose up --build
# Frontend: http://localhost:5173 — API docs: http://localhost:8000/docs
```

## Documentation

Full documentation lives in [docs/](docs/):

| Document | For whom | Contents |
| --- | --- | --- |
| [user-guide.md](docs/user-guide.md) | Everyday users | Signing in, managing plants/locations, logging care, reminders, calendar, notifications |
| [setup.md](docs/setup.md) | Operators deploying it | Local development, docker-compose, Kubernetes/ArgoCD, building images |
| [administration.md](docs/administration.md) | Operators running it | Configuration reference, Zitadel/ntfy/FloraCodex setup, backups, migrations, monitoring, security, troubleshooting |
| [architecture.md](docs/architecture.md) | Developers & curious operators | Tech stack, auth flow, reminder engine, data model, API reference |
| [development.md](docs/development.md) | Contributors | Running locally, tests, e2e, regenerating API types, conventions |

The original product specification lives in [SPEC.md](SPEC.md).
