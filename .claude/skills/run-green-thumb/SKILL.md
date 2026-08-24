---
name: run-green-thumb
description: Start Green Thumb locally (FastAPI backend + Vite SPA) with the dev-login bypass so a change can be seen in the real app, optionally with demo data. Use when asked to run, start, open, or screenshot the app, or to check a change in the UI rather than only in tests.
---

# Running Green Thumb locally

Two processes: the FastAPI backend on `:8000` and the Vite dev server on
`:5173`, which proxies `/api` and `/auth` to the backend. Both must run; opening
`:5173` alone gives a shell that 401s on every request.

## 1. Check the ports and migrate

```bash
(ss -ltn 2>/dev/null || netstat -ltn) | grep -E ':(8000|5173)'   # expect no output
uv run alembic upgrade head                                      # local dev DB: ./greenthumb.db
```

`greenthumb.db` is gitignored local dev data. Migrations are additive and
`alembic downgrade` works, but check whether it holds plants worth keeping
before doing anything destructive to it.

## 2. Start both servers in the background

```bash
DEV_AUTH_BYPASS=true SESSION_COOKIE_SECURE=false SESSION_SECRET_KEY=local-dev-secret \
  uv run uvicorn greenthumb.main:app --port 8000

cd frontend && npm run dev
```

`DEV_AUTH_BYPASS=true` enables `GET /auth/dev-login`, which provisions a demo
user and sets a session cookie with no Zitadel round-trip. `SESSION_COOKIE_SECURE=false`
is required over plain http — without it the browser drops the cookie and every
page looks logged out. Never set either in a deployed environment.

Smoke both before going further:

```bash
curl -s -o /dev/null -w "backend:%{http_code}\n" localhost:8000/healthz
curl -s -o /dev/null -w "spa:%{http_code}\n"     localhost:5173/
```

## 3. Seed demo data (optional)

A fresh database shows an empty dashboard. `seed_demo_data.py` (next to this
file) creates a location, three species covering the interesting cases, five
plants and backdated watering logs, all through the real API:

```bash
uv run python .claude/skills/run-green-thumb/seed_demo_data.py
```

It prints the current season and a dashboard summary. Re-running adds
duplicates; it does not clean up after itself.

## 4. Drive it

`chromium-cli` is not installed, but Playwright is, in `frontend/`. **Node
resolves `@playwright/test` from `frontend/node_modules`, so the script must
live in `frontend/` — a script in a scratchpad directory fails with
`ERR_MODULE_NOT_FOUND` even when run with `frontend` as the cwd.** Write it to
`frontend/`, run it, delete it.

```javascript
import { chromium } from '@playwright/test';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 950 } });
await page.goto('http://localhost:8000/auth/dev-login');   // sets the session cookie
await page.goto('http://localhost:5173/');
await page.waitForSelector('text=Dashboard');
await page.screenshot({ path: '/tmp/dashboard.png', fullPage: true });
await browser.close();
```

Look at the screenshot; a blank frame means the SPA failed to boot, not that the
page is empty.

Modal content (the species form) scrolls inside the modal, so `fullPage` cuts it
off and `scrollIntoViewIfNeeded()` does not move it. Use the wheel:

```javascript
await page.mouse.move(640, 500);
await page.mouse.wheel(0, 900);
```

## Gotchas worth knowing

- **`npm run generate-types` is broken.** The frontend is on TypeScript 7 while
  `openapi-typescript@7` needs the TypeScript 5 compiler API, so it dies on
  `ts.factory` being undefined. Regenerate from a directory *outside* the repo,
  or npm resolves the broken local install anyway:

  ```bash
  SESSION_SECRET_KEY=x uv run python -c "import json; from greenthumb.main import app; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
  cd "$(mktemp -d)" && npx -y -p typescript@5.9.3 -p openapi-typescript@7.13.0 \
    openapi-typescript /workspaces/plant-manager/openapi.json \
    -o /workspaces/plant-manager/frontend/src/api/types.gen.ts
  ```

- **Seasonal behaviour depends on today's date.** Watering paces and paused
  reminders only show if the current season triggers them. To see a pause in
  summer, use the `winter_grower` preset (it rests in summer); the seed script's
  Cyclamen covers this.

- The e2e suite starts its own backend and SPA on a throwaway
  `greenthumb-e2e.db` — don't run `npm run test:e2e` expecting it to use the
  servers above, and stop nothing on its account.

## Quality gate

```bash
uv run ruff check --fix . && uv run ruff format . && uv run ty check
uv run pytest
cd frontend && npm run build          # tsc -b + vite build
cd frontend && npm run test:e2e       # local only, not in CI
```
