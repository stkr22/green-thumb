import { test, expect } from '@playwright/test';

// Unique suffix per run so tests don't collide with each other or with data
// left by earlier runs in the shared SQLite file.
const stamp = () => `${Date.now()}-${Math.floor(Math.random() * 1000)}`;

test('create a location, then a plant in it', async ({ page }) => {
  const id = stamp();
  const locationName = `Greenhouse ${id}`;
  const plantName = `Aloe ${id}`;

  await page.goto('/locations');
  await page.getByPlaceholder('New location').fill(locationName);
  await page.getByRole('button', { name: 'Add' }).click();
  await expect(page.getByText(locationName)).toBeVisible();

  await page.goto('/plants/new');
  await page.getByPlaceholder('My Monstera').fill(plantName);
  await page.getByPlaceholder('tropical, low-light').fill('succulent, easy-care');
  await page.getByRole('combobox').selectOption({ label: locationName });
  await page.getByRole('button', { name: 'Create plant' }).click();

  // Redirected to the new plant's detail page.
  await expect(page.getByRole('heading', { name: plantName })).toBeVisible();
  await expect(page.getByText(locationName)).toBeVisible();

  // And it appears in the plant grid.
  await page.goto('/plants');
  await expect(page.getByText(plantName)).toBeVisible();
});

test('logging watering updates the care summary and timeline', async ({ page }) => {
  const id = stamp();
  const plantName = `Fern ${id}`;

  await page.goto('/plants/new');
  await page.getByPlaceholder('My Monstera').fill(plantName);
  await page.getByRole('button', { name: 'Create plant' }).click();
  await expect(page.getByRole('heading', { name: plantName })).toBeVisible();

  await page.getByRole('button', { name: 'Water' }).click();

  // Toast confirms the mutation, the summary flips to "today", and a Watering
  // row is inserted into the care log.
  await expect(page.getByText('Water logged')).toBeVisible();
  await expect(page.getByText('today')).toBeVisible();
  // A watering row is inserted into the care log (scope to the list item so we
  // don't match the event-type filter's <option>).
  const careLog = page.locator('section', { hasText: 'Care log' });
  await expect(careLog.locator('li').filter({ hasText: /watering/i })).toBeVisible();
});

test('adding a reminder lists it and surfaces it on the dashboard', async ({ page }) => {
  const id = stamp();
  const plantName = `Cactus ${id}`;

  await page.goto('/plants/new');
  await page.getByPlaceholder('My Monstera').fill(plantName);
  await page.getByRole('button', { name: 'Create plant' }).click();
  await expect(page.getByRole('heading', { name: plantName })).toBeVisible();

  // Add a watering reminder (the event field defaults to "watering").
  await page.getByRole('button', { name: 'Add' }).click();
  await expect(page.getByText('every 7 days')).toBeVisible();

  // A reminder with no matching care log is immediately overdue on the dashboard.
  await page.goto('/');
  const overdue = page.locator('section', { hasText: 'Overdue' });
  await expect(overdue.getByText(plantName)).toBeVisible();
});
