import { test as setup, expect } from '@playwright/test';

// Authenticate once via the dev-login bypass and persist the session cookie so
// every test starts logged in. This stands in for the OIDC flow, which can't
// run without a live Zitadel.
const authFile = 'e2e/.auth/state.json';

setup('authenticate via dev-login', async ({ page }) => {
  await page.goto('/auth/dev-login');
  // dev-login sets the cookie and 302-redirects to the dashboard.
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await page.context().storageState({ path: authFile });
});
