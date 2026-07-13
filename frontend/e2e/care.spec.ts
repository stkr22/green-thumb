import { test, expect } from '@playwright/test';

// Unique suffix per run so tests don't collide with each other or with data
// left by earlier runs in the shared SQLite file.
const stamp = () => `${Date.now()}-${Math.floor(Math.random() * 1000)}`;

async function createPlant(page: import('@playwright/test').Page, plantName: string) {
  await page.goto('/plants/new');
  await page.getByPlaceholder('My Monstera').fill(plantName);
  await page.getByRole('button', { name: 'Create plant' }).click();
  await expect(page.getByRole('heading', { name: plantName })).toBeVisible();
}

test('undo restores the care card after an accidental tap', async ({ page }) => {
  const plantName = `Ivy ${stamp()}`;
  await createPlant(page, plantName);

  const waterCard = page.getByRole('button', { name: 'Water' });
  await expect(waterCard.getByText('Watered never')).toBeVisible();

  await waterCard.click();
  await expect(waterCard.getByText('Watered today')).toBeVisible();

  await page.getByRole('button', { name: 'Undo' }).click();
  await expect(waterCard.getByText('Watered never')).toBeVisible();
});

test('a due plant shows a colored chip on its overview card', async ({ page }) => {
  const plantName = `Palm ${stamp()}`;
  await createPlant(page, plantName);

  // A watering reminder without any care log is immediately due.
  await page.getByRole('button', { name: 'Add' }).click();
  await expect(page.getByText('every 7 days')).toBeVisible();

  await page.goto('/plants');
  const card = page.locator('a', { hasText: plantName });
  await expect(card.getByText('Water due')).toBeVisible();
});

test('snoozing an overdue reminder moves it out of the overdue list', async ({ page }) => {
  const plantName = `Basil ${stamp()}`;
  await createPlant(page, plantName);
  await page.getByRole('button', { name: 'Add' }).click();
  await expect(page.getByText('every 7 days')).toBeVisible();

  await page.goto('/');
  const overdue = page.locator('section', { hasText: 'Overdue' });
  const row = overdue.locator('a', { hasText: plantName });
  await expect(row).toBeVisible();

  await row.getByTitle(/^Snooze watering/).click();
  await expect(page.getByText(/watering snoozed for 7 days/)).toBeVisible();

  // Gone from Overdue; parked in the upcoming list labeled as snoozed.
  await expect(overdue.locator('a', { hasText: plantName })).toHaveCount(0);
  const upcoming = page.locator('section', { hasText: 'Next 7 days' });
  const snoozedRow = upcoming.locator('a', { hasText: plantName });
  await expect(snoozedRow).toBeVisible();
  await expect(snoozedRow.getByText('snoozed')).toBeVisible();
});
