import { expect, test } from './fixtures';

// Smoke test: every primary page renders for an authenticated user and the
// navigation reaches each of them (lazy route chunks included).
test('navigates between all main pages', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  // The current user is shown in the sidebar footer.
  await expect(page.getByText('Demo Gardener')).toBeVisible();

  for (const name of ['Plants', 'Species', 'Locations', 'Calendar', 'Profile'] as const) {
    await page.getByRole('link', { name, exact: true }).click();
    await expect(page.getByRole('heading', { name, level: 1 })).toBeVisible();
  }
});

test('unknown routes and missing plants explain themselves instead of spinning', async ({ page }) => {
  await page.goto('/no-such-page');
  await expect(page.getByText("This page doesn't exist.")).toBeVisible();

  await page.goto('/plants/00000000-0000-0000-0000-000000000000');
  await expect(page.getByText("This plant doesn't exist (any more).")).toBeVisible();
  await page.getByRole('link', { name: 'All plants' }).click();
  await expect(page.getByRole('heading', { name: 'Plants', level: 1 })).toBeVisible();
});

test('a failed page load shows the error page, and Try again recovers', async ({ page }) => {
  // Fail the dashboard's data exactly twice (the request plus its one retry),
  // then let it through: the retry button must re-run the route loader.
  let failures = 0;
  await page.route('**/api/v1/dashboard?*', (route) =>
    failures++ < 2 ? route.fulfill({ status: 500, json: { detail: 'Database is busy' } }) : route.continue(),
  );

  await page.goto('/');
  await expect(page.getByText("Couldn't load this page.")).toBeVisible();
  await expect(page.getByText('Database is busy')).toBeVisible();
  // The navigation stays usable while the page itself failed.
  await expect(page.getByRole('link', { name: 'Plants', exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard', level: 1 })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
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
