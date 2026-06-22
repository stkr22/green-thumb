# Architecture

Technical overview of how Green Thumb is built. For day-to-day development
tasks see [development.md](development.md); for operating it see
[administration.md](administration.md).

## Components

| Component | Technology | Path |
| --- | --- | --- |
| Backend API | FastAPI + SQLModel (async, aiosqlite), Python 3.14 | `src/greenthumb/` |
| Migrations | Alembic | `alembic/` |
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS 4 + TanStack Query 5 | `frontend/` |
| Database | SQLite (single file) | PVC in production |
| Deployment | Helm chart (OCI), synced by ArgoCD | `charts/green-thumb/` |
| Local dev | docker-compose (backend + frontend) | `docker-compose.yml` |

The SPA and API share one origin in production: the FastAPI backend serves the
built SPA at `/` alongside the API, so there is no CORS configuration. Traefik
forwards the whole hostname to the backend.

```
                      ┌──────────────── Traefik (one hostname) ───────────────┐
   browser  ──────▶   │  /*  → backend (FastAPI: API + static SPA)            │
                      └───────────────────────────────────────────────────────┘
                                   │                         │
                                   ▼                         ▼
                            SQLite file (PVC)          Zitadel / ntfy
```

## Why SQLite / single-instance

The app is single-household and single-instance by design: the hourly reminder
loop runs **in-process** (a FastAPI lifespan task), so running more than one
replica would double-send notifications. At that scale SQLite removes the
operational weight of a separate database (no operator, one file to back up)
without giving up anything the app uses.

The trade-off is that the backend is **stateful**: it owns a `ReadWriteOnce`
volume and deploys with the `Recreate` strategy (brief downtime per rollout).
This is a deliberate choice documented in the project history; don't switch to
multiple replicas or `RollingUpdate` without first moving the scheduler out of
process and the database to a networked store.

## Backend layout

- `config.py` — pydantic-settings configuration; all values from the environment.
- `db.py` — lazy async engine + request-scoped session dependency. Sets SQLite
  `foreign_keys`, `journal_mode=WAL`, and `busy_timeout` pragmas on connect.
- `models/` — SQLModel table models. Tag lists and free-form dicts are `JSON`
  columns; datetimes are normalised with `models.base.ensure_utc`.
- `schemas/` — Pydantic/SQLModel request & response models.
- `auth/` — OIDC client, signed-cookie sessions, and the `get_current_user`
  dependency.
- `api/v1/` — one router module per domain; handlers stay thin.
- `services/` — business logic: `ntfy`, care-log queries (`care`), and
  `reminder_evaluator`.
- `main.py` — app wiring, `/healthz` & `/readyz`, and the reminder loop started
  in the lifespan handler.

Route handlers are intentionally thin; anything non-trivial lives in `services/`.

## Authentication

The backend implements the full OIDC authorization-code flow with PKCE itself
(no auth sidecar). Sessions are **stateless signed cookies** — an HS256 JWT
signed with `SESSION_SECRET_KEY` — so there is no server-side session store.

1. `GET /auth/login` — generates `state`, `nonce`, and a PKCE verifier, stores
   them in a short-lived signed **flow cookie**, and redirects to Zitadel's
   authorize endpoint.
2. `GET /auth/callback` — validates `state` against the flow cookie, exchanges
   the code at the token endpoint (POST auth + PKCE), verifies the ID token
   against Zitadel's JWKS (issuer, audience, nonce), upserts the user (keyed by
   the OIDC `sub`), sets the session cookie, and redirects to `FRONTEND_URL`.
   Email/name fall back to the userinfo endpoint when absent from the ID token.
3. `GET /auth/logout` — clears the session cookie and redirects to Zitadel's
   end-session endpoint.
4. Protected routes depend on `get_current_user`, which validates the session
   cookie and loads the `User`. Missing/invalid → `401`, which makes the SPA
   redirect to `/auth/login`.

OIDC discovery and JWKS are fetched from the issuer and cached (1h). There is a
local-only `GET /auth/dev-login` bypass gated by `DEV_AUTH_BYPASS`
(see [administration.md](administration.md#dev-login-bypass-local-only)).

> **No authorization layer.** Authentication proves identity, but there are no
> roles and no per-user filtering — every authenticated user has full access to
> all data. This is intentional for a shared household instance.

## Reminder evaluation

A background task (`reminder_evaluator.evaluate_and_notify`) runs every
`REMINDER_CHECK_INTERVAL_SECONDS` (default hourly). For each **enabled**
reminder it finds the most recent matching care log and computes due state:

- **Overdue** when there is no matching care log, or `now - last_logged_at >
  interval_days`.
- Overdue reminders are pushed via ntfy to every user with `ntfy_enabled =
  true`, using each user's topic override or the global `NTFY_TOPIC`.
- **De-duplication:** after notifying, `last_notified_at` is stamped on the
  reminder and it won't re-notify until another `interval_days / 2` has passed —
  so an ignored reminder doesn't fire every hour.

The same due-state computation backs the `/dashboard` endpoint, so the dashboard
and the notifications always agree on what's overdue.

## Photos

Photos are stored as BLOBs in SQLite and served by `GET /api/v1/photos/{id}`
with the stored `Content-Type`, so the frontend uses plain `<img>` tags (no
TanStack Query). Uploads are `multipart/form-data`, image-only, capped at 15 MB.

On upload each image is decoded, downscaled, and re-encoded to WebP into two
variants (`services/images.py`): a display image (longest edge 2048 px) served by
`GET /photos/{id}` and a thumbnail (longest edge 400 px) served by
`GET /photos/{id}/thumb` for grids and cards. The original is not retained — this
strips EXIF (including GPS) and keeps inline BLOBs small. Re-encoding is CPU-bound
and runs in a threadpool so it never blocks the single-instance event loop.
Inline BLOBs still grow the database file — see
[administration.md](administration.md#database--backups) for backup guidance.

## Data model

Six tables, all with UUID primary keys and UTC timestamps:

- **users** — `oidc_sub` (unique identity), `email`, `display_name`,
  `ntfy_enabled`, `ntfy_topic_override`.
- **locations** — `name`, `description`, `created_by` → users.
- **plants** — `name`, `species_name`, `scientific_name`, `location_id` →
  locations (`SET NULL` on delete), `notes`, `tags` (string list),
  `cover_photo_id` → plant_photos (`SET NULL`), `created_by`, timestamps.
- **plant_photos** — `plant_id` → plants (`CASCADE`), `data` (display BLOB),
  `thumbnail` (BLOB), `mime_type`, `uploaded_by`.
- **care_logs** — `plant_id` → plants (`CASCADE`), `event_type`, `notes`,
  `logged_at` (user-supplied/backdatable), `logged_by`.
- **reminders** — `plant_id` → plants (`CASCADE`), `event_type`,
  `interval_days`, `enabled`, `last_notified_at`, `created_by`.

`plants` and `plant_photos` reference each other (a plant's cover photo, and a
photo's plant). Because SQLite cannot add a foreign key via `ALTER TABLE`, the
initial migration declares the `cover_photo_id` FK inline (SQLite permits a
forward reference to a table created later).

## API reference

All `/api/v1/*` and `/auth/me` routes require a valid session cookie.

**Auth** (`/auth`)
| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/auth/login` | Start OIDC login |
| GET | `/auth/callback` | OIDC redirect target |
| GET | `/auth/logout` | Clear session, end-session redirect |
| GET | `/auth/me` | Current user profile + ntfy settings |
| PATCH | `/auth/me` | Update `ntfy_enabled`, `ntfy_topic_override` |
| GET | `/auth/dev-login` | Local-only bypass (404 unless `DEV_AUTH_BYPASS`) |

**Locations** (`/api/v1`)
| Method | Path |
| --- | --- |
| GET / POST | `/locations` |
| PATCH / DELETE | `/locations/{id}` |

**Plants**
| Method | Path | Notes |
| --- | --- | --- |
| GET | `/plants` | `?location_id=`, `?tag=`, `?search=` |
| POST | `/plants` | |
| GET / PATCH / DELETE | `/plants/{id}` | detail includes last event per type |
| POST | `/plants/{id}/cover` | set cover photo |

**Photos**
| Method | Path |
| --- | --- |
| GET / POST | `/plants/{id}/photos` |
| GET / DELETE | `/photos/{id}` |
| GET | `/photos/{id}/thumb` |

**Care logs**
| Method | Path | Notes |
| --- | --- | --- |
| GET / POST | `/plants/{id}/logs` | `?event_type=`, `?limit=`, `?offset=` |
| DELETE | `/logs/{id}` | |

**Reminders**
| Method | Path |
| --- | --- |
| GET / POST | `/plants/{id}/reminders` |
| PATCH / DELETE | `/reminders/{id}` |

**Other**
| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/dashboard` | Overdue/upcoming reminders, recent care, counts (`?upcoming_days=`) |
| POST | `/notifications/test` | Send a test ntfy notification |
| GET | `/healthz`, `/readyz` | Liveness / readiness |

Interactive docs (Swagger UI) are served at `/docs` on a running backend, and
the OpenAPI schema is the source of truth for the typed frontend client (see
[development.md](development.md#regenerating-the-api-client)).
