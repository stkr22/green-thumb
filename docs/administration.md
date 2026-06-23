# Administration

Running and operating Green Thumb: configuration, external-service setup,
backups, migrations, monitoring, security, and troubleshooting. For deployment
mechanics see [setup.md](setup.md).

## Configuration reference

All configuration comes from environment variables (validated by
pydantic-settings in `src/greenthumb/config.py`). In production these are
supplied by the `green-thumb-backend` Kubernetes secret; locally via `.env`
or `.env.local`.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | no | `sqlite+aiosqlite:///./greenthumb.db` | SQLite URL. Production uses an absolute path on the PVC: `sqlite+aiosqlite:////data/greenthumb.db` (note four slashes) |
| `OIDC_ISSUER_URL` | yes¹ | — | Zitadel issuer, e.g. `https://auth.example.com` |
| `OIDC_CLIENT_ID` | yes¹ | — | Zitadel application client ID |
| `OIDC_CLIENT_SECRET` | yes¹ | — | Zitadel application client secret |
| `OIDC_REDIRECT_URI` | yes¹ | — | Must match the app registration, e.g. `https://plants.example.com/auth/callback` |
| `SESSION_SECRET_KEY` | **yes** | — | Random secret used to sign session cookies (HS256). Generate with `openssl rand -hex 32` |
| `SESSION_COOKIE_SECURE` | no | `true` | Set `false` only for plain-HTTP local dev |
| `SESSION_MAX_AGE_SECONDS` | no | `604800` (7 days) | Session cookie lifetime |
| `FRONTEND_URL` | yes | `http://localhost:5173` | Where login/logout redirect back to |
| `NTFY_URL` | no | — | ntfy server URL; notifications are skipped if unset |
| `NTFY_TOPIC` | no | `greenthumb` | Default notification topic |
| `NTFY_TOKEN` | no | — | ntfy bearer access token (see [ntfy](#ntfy-push-notifications)) |
| `REMINDER_CHECK_INTERVAL_SECONDS` | no | `3600` | How often the reminder loop runs (min 60) |
| `LOG_LEVEL` | no | `INFO` | Python log level |
| `DEV_AUTH_BYPASS` | no | `false` | **Local only.** Enables `GET /auth/dev-login`; see [below](#dev-login-bypass-local-only) |
| `DEV_AUTH_EMAIL` | no | `demo@example.com` | Demo user email when the bypass is on |
| `DEV_AUTH_DISPLAY_NAME` | no | `Demo Gardener` | Demo user name when the bypass is on |

¹ Required for real login. The app will start without them, but `/auth/login`
returns `503` until they're set (or use the dev-login bypass).

## Zitadel (OIDC) setup

Green Thumb performs the full OIDC authorization-code flow with PKCE itself —
no auth proxy. Create an application in your Zitadel project:

- **Application type:** Web (confidential — the backend holds the secret)
- **Grant type:** Authorization Code (PKCE is also sent; leave it enabled)
- **Authentication method:** **POST** (`client_secret_post`). This must match —
  Zitadel's default is *Basic*, which causes the token exchange to fail with
  `invalid_client`.
- **Redirect URI:** your callback, exactly. Production:
  `https://plants.example.com/auth/callback`. Local same-origin dev:
  `http://localhost:5173/auth/callback`.
- **Post-logout redirect URI:** your `FRONTEND_URL`.
- **Development mode (allow http):** enable only for local HTTP testing.

The app requests the scopes `openid profile email`. Email is read from the ID
token, falling back to the userinfo endpoint if absent. Map those into:

- `OIDC_ISSUER_URL` (no trailing slash needed — it's normalised)
- `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI`

Endpoints (authorize, token, JWKS, userinfo, end-session) are discovered
automatically from `{issuer}/.well-known/openid-configuration`, so only the
issuer is needed.

### Verifying the integration

```bash
# Discovery is reachable from the backend's network:
curl -s https://auth.example.com/.well-known/openid-configuration | jq '.issuer, .token_endpoint'

# /auth/login builds a correct authorize redirect (no credentials needed):
curl -s -o /dev/null -D - http://localhost:8000/auth/login | grep -i location
```

The redirect should point at the issuer's `authorize` endpoint with your
`client_id`, the registered `redirect_uri`, `scope=openid profile email`, and a
PKCE `code_challenge`. A successful browser login logs (at `INFO`):

```
POST .../oauth/v2/token  200 OK
Provisioned new user for sub=...
GET /auth/callback?...    302 Found
GET /auth/me              200 OK
```

## ntfy push notifications

Notifications use [ntfy](https://ntfy.sh). Set `NTFY_URL` and `NTFY_TOPIC`; for
an authenticated ntfy server, set `NTFY_TOKEN`.

- **Authentication:** only **bearer access tokens** are supported. Create one in
  ntfy (`ntfy token add <user>`) and set it as `NTFY_TOKEN`; it's sent as
  `Authorization: Bearer <token>`.
- **HTTP Basic auth (username/password) is not supported.** Use an access token
  instead. (If you need Basic auth, it would require a small code change in
  `services/ntfy.py`.)
- **Per-user topics:** each user can set a topic override on their Profile page;
  notifications for that user go to their topic instead of `NTFY_TOPIC`.

Notification delivery never blocks the app — failures are logged and ignored, so
a down ntfy server won't break care logging or the reminder loop. Users can
verify their own setup with **Send test notification** on the Profile page;
operators can check the server config the same way (it returns `502` if ntfy
rejects the publish).

## Database & backups

The entire application state is one SQLite file (including photos, stored as
BLOBs). The engine runs in WAL mode with foreign keys enforced and a busy
timeout (set on connect in `db.py`).

### Backups

Because photos are inline, the file can grow; prefer streaming backups over
plain copies as it does:

- **PVC snapshots** — snapshot the `green-thumb-data` volume on a schedule
  (simplest if your storage supports it).
- **[Litestream](https://litestream.io)** — run as a sidecar to stream the WAL
  to object storage continuously (supports point-in-time restore).
- **Manual / ad-hoc** — use SQLite's online backup so you copy a consistent
  snapshot even while the app is running:
  ```bash
  # inside the backend container/pod, /data is the volume
  sqlite3 /data/greenthumb.db ".backup '/data/backup-$(date +%F).db'"
  ```
  Then copy the backup file off the volume (`kubectl cp`).

### Restore

Stop the backend (scale the Deployment to 0), replace `/data/greenthumb.db` (and
remove stale `-wal`/`-shm` files) with your backup, then scale back up. The
migration initContainer will no-op if the schema is already current.

## Migrations

Schema changes are managed with Alembic. The production initContainer runs
`alembic upgrade head` before the app starts on every rollout.

```bash
uv run alembic upgrade head                       # apply pending migrations
uv run alembic revision --autogenerate -m "..."   # author a new migration
uv run alembic downgrade -1                        # roll back one (if needed)
```

SQLite cannot `ALTER` columns/constraints in place, so autogenerated migrations
use Alembic **batch mode** (table rebuilds), enabled in `alembic/env.py`.
Always verify a new migration by running `alembic upgrade head` against a
throwaway SQLite file before shipping it.

## Monitoring & health

| Endpoint | Meaning |
| --- | --- |
| `GET /healthz` | Liveness — the process is up |
| `GET /readyz` | Readiness — the database answers a trivial query |

Both are used as Kubernetes probes. Logs go to stdout at `LOG_LEVEL`; the auth
and reminder paths log meaningful events (user provisioning, OIDC failures,
notifications sent).

## User management

- **Provisioning is automatic.** A user record is created on first successful
  login, keyed by the OIDC `sub` claim. Email and display name are refreshed
  from the IdP on each login.
- **No roles or admin UI.** There is no concept of admin vs. normal user, and no
  per-user data isolation — **every authenticated user can see and edit all
  data.** Control access by controlling who is allowed into the Zitadel
  application (e.g. via Zitadel project authorizations/roles).
- **Removing a user** — revoke their access in Zitadel. To also delete their
  record, remove the row from the `users` table directly (there is no API for
  it). Note that `locations`, `plants`, `care_logs` and `reminders` reference
  `users.id` via foreign keys, so historical rows they created will block a
  delete unless reassigned/removed first.

## Security notes

- **Rotate `SESSION_SECRET_KEY`** if it may have leaked — doing so invalidates
  all existing sessions (everyone re-logs in).
- **Rotate the OIDC client secret** in Zitadel if it may have been exposed, and
  update the `green-thumb-backend` secret.
- **Keep `SESSION_COOKIE_SECURE=true`** in production (the default). It's only
  safe to disable behind plain-HTTP localhost.
- **Never enable `DEV_AUTH_BYPASS`** anywhere reachable — it lets anyone obtain a
  session with no credentials.
- The app stores **no passwords**; authentication is delegated entirely to
  Zitadel.

### Dev-login bypass (local only)

When `DEV_AUTH_BYPASS=true`, `GET /auth/dev-login` provisions a demo user
(`DEV_AUTH_EMAIL` / `DEV_AUTH_DISPLAY_NAME`) and sets a valid session cookie
without contacting Zitadel — useful for local UI work and end-to-end tests.
While the flag is `false` (the default), the route returns `404`. This is
covered by tests (`tests/test_dev_login.py`) to ensure it stays inert by default.

### API tokens (headless access)

For scripts or agents that call the API without a browser, mint a long-lived
bearer token for an existing user:

```bash
uv run python scripts/mint_api_token.py user@example.com
```

Send the printed token as `Authorization: Bearer <token>`; it authenticates
exactly like a session cookie. Tokens are stateless signed JWTs (90-day life),
so an individual token **cannot** be revoked — rotate `SESSION_SECRET_KEY` to
invalidate every token and session at once. The user must already exist (log in
via Zitadel, or the dev-login bypass, once first).

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| `/auth/login` returns `503` | `OIDC_*` not configured, or discovery URL unreachable from the backend. Check `OIDC_ISSUER_URL` and network egress. |
| Zitadel shows a redirect-URI error | The `OIDC_REDIRECT_URI` doesn't exactly match a registered redirect URI in the app. |
| Login fails, log shows `Token exchange failed` / `invalid_client` | App auth method isn't **POST**, or the client secret is wrong. |
| Login fails, log shows `ID token validation failed` | Issuer/audience/nonce mismatch — confirm `OIDC_ISSUER_URL` and that `OIDC_CLIENT_ID` is in the token audience. |
| Endless redirect to login after signing in | Session cookie not being stored. Over HTTP set `SESSION_COOKIE_SECURE=false`; ensure the browser reaches the app on the same origin as `FRONTEND_URL`. |
| Test notification returns `502` | ntfy rejected the publish — check `NTFY_URL`, `NTFY_TOKEN`, and that the topic is writable. |
| `readyz` failing | The database file/volume isn't writable or reachable; check the PVC and `fsGroup`. |
| Deploy hangs / `Multi-Attach` error on the PVC | The volume is `ReadWriteOnce`; ensure the old pod is gone (the `Recreate` strategy handles this — don't switch to `RollingUpdate`). |
