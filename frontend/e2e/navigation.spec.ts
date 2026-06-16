import { test, expect } from '@playwright/test';

// Smoke test: every primary page renders for an authenticated user and the
// sidebar navigation works.
test('navigates between all main pages', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  // The current user is shown in the sidebar footer.
  await expect(page.getByText('Demo Gardener')).toBeVisible();

  for (const name of ['Plants', 'Locations', 'Calendar', 'Profile'] as const) {
    await page.getByRole('link', { name }).click();
    await expect(page.getByRole('heading', { name })).toBeVisible();
  }
});

test('unauthenticated access is rejected by the API', async ({ playwright }) => {
  // A fresh request context has no session cookie (unlike the project default,
  // which loads the saved storageState). Hit the backend directly to avoid the
  // SPA proxy so we assert on the API's own response.
  const ctx = await playwright.request.newContext({ baseURL: 'http://127.0.0.1:8000' });
  const response = await ctx.get('/api/v1/plants');
  expect(response.status(), 'plants list without a session cookie').toBe(401);
  await ctx.dispose();
});
