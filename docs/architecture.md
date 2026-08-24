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
built SPA at `/` alongside the API (via `app.frontend()`), so there is no CORS
configuration. Traefik forwards the whole hostname to the backend.

Path operations win over the static files, and the `index.html` fallback only
applies to requests that accept HTML. So a browser deep link like `/plants/123`
resolves to the SPA shell, while a stale asset or an unknown `/api` path still
returns a real `404` instead of an HTML page.

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
- **Snooze:** a user can defer a due reminder (`snoozed_until`); the effective
  due date is `max(last log + interval, snoozed_until)`, so a snoozed reminder
  is neither overdue nor notified until the snooze expires. Logging a matching
  care event clears the snooze — it must never outlive a real care event.
- Overdue reminders are pushed via ntfy to every user with `ntfy_enabled =
  true`, using each user's topic override or the global `NTFY_TOPIC`.
- **De-duplication:** after notifying, `last_notified_at` is stamped on the
  reminder and it won't re-notify until another `interval_days / 2` has passed —
  so an ignored reminder doesn't fire every hour.

The same due-state computation backs the `/dashboard` endpoint, so the dashboard
and the notifications always agree on what's overdue.

### Seasonal pacing

`interval_days` is the **growing-season** pace. A reminder may carry
`season_multipliers` (season → multiplier, `null` to suspend), and
`services/seasons.py` turns that into a due date.

Due dates come from **accumulating a daily rate** — day *d* contributes
`1 / (interval_days × multiplier(season(d)))`, and the reminder is due on the
day the running total reaches 1.0 — rather than from multiplying the interval by
today's multiplier. Multiplying by the current season would move every due date
the instant the season flips, turning a whole collection overdue on 1 March;
accumulating prices days already spent at the winter pace at the winter pace.
It also makes suspension fall out for free: a suspended day contributes 0, so a
paused event type accrues nothing and comes due a full interval after the
growing season resumes. With no plan, the accumulation reduces exactly to
`last_logged_at + interval_days`, which is asserted directly in `tests/test_seasons.py`.

A **paused** reminder (the current season's multiplier is `null`) never counts
as overdue and never notifies; its `due_at` reports the resume date instead, so
the UI can label it rather than show a stale overdue date. Re-notification
back-off and the snooze default both use the season's effective interval, not
the base one.

`multiplier_for()` is the only seam that knows about discrete seasons — swapping
in a smooth daylength curve from latitude would not touch the rest.

Which months map to which season comes from the `HEMISPHERE` setting: it is
deployment-wide rather than per-user, because plants are shared between users
and a household sits in one hemisphere.

### Annual-window reminders

Season plans are **not** a fit for jobs that belong in a fixed window
(repotting, pruning, overwintering): suspending three seasons of a two-year
repotting interval would stretch it to roughly four years, since only active
days accrue. Those use `schedule_kind = "annual_window"` with inclusive
`window_start_month` / `window_end_month`, which may wrap the year.

The two kinds mean different things and are mutually exclusive per reminder:

| | interval | annual_window |
|---|---|---|
| Interval | scaled by `season_multipliers` | runs at full speed |
| Dormant time | accrues nothing while suspended | accrues normally |
| Effect | the schedule slows down | only the due date is deferred |

A window reminder's due date is `last_logged_at + interval_days`, pushed forward
by `seasons.next_window_start` to the next time the window opens (a snooze is
applied before the deferral, so a snooze landing out of season is deferred too).
Season multipliers are ignored for these — the window already says when the job
may happen — and `paused` is always false.

Months are stored literally rather than as seasons, so they mean the same thing
in both hemispheres; the UI offers a season as a shortcut that fills the months
using `seasons.months_for`.

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
  `interval_days`, `season_multipliers` (JSON: season → multiplier, `null`
  suspends; empty means no seasonal change), `schedule_kind` (`interval` |
  `annual_window`), `window_start_month` / `window_end_month`, `enabled`,
  `last_notified_at`, `created_by`.

`schedule_kind` is a plain string column rather than a SQL enum: SQLite cannot
`ALTER TABLE ADD COLUMN` with the CHECK constraint `sa.Enum` emits, so the
allowed values are enforced by `models.reminder.ScheduleKind` and the request
schemas instead.

`species.default_intervals`, `species.season_plan` (JSON: event type → season →
multiplier) and `species.default_windows` (JSON: event type → `[start_month,
end_month]`) are all **materialized** onto a plant's reminders at creation
rather than read live, so tuning one plant never affects its siblings. The
trade-off is that editing a species does not reach plants that already exist;
`POST /species/{id}/apply-season-plan` is the explicit opt-in that rolls the
pace and windows out to them, leaving per-plant intervals alone.

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
