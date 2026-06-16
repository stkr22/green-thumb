import { defineConfig, devices } from '@playwright/test';

// End-to-end tests drive the real SPA against a real backend. Playwright starts
// both servers itself: an isolated backend on a throwaway SQLite file with the
// dev-login bypass enabled (no Zitadel needed), and the Vite dev server which
// proxies /api and /auth to it. Auth runs once in a setup project and is reused
// via storageState.
export default defineConfig({
  testDir: './e2e',
  // Tests share one SQLite file and one single-instance backend, so run serially.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/state.json' },
      dependencies: ['setup'],
    },
  ],
  webServer: [
    {
      // Run from the repo root; recreate a clean DB and migrate before serving.
      command:
        'uv run sh -c "rm -f greenthumb-e2e.db greenthumb-e2e.db-wal greenthumb-e2e.db-shm && alembic upgrade head && uvicorn greenthumb.main:app --host 127.0.0.1 --port 8000"',
      cwd: '..',
      url: 'http://127.0.0.1:8000/healthz',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        SESSION_SECRET_KEY: 'e2e-test-secret-key',
        SESSION_COOKIE_SECURE: 'false',
        DATABASE_URL: 'sqlite+aiosqlite:///./greenthumb-e2e.db',
        DEV_AUTH_BYPASS: 'true',
        FRONTEND_URL: 'http://localhost:5173',
      },
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
