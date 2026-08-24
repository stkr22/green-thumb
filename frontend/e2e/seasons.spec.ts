import { test, expect } from '@playwright/test';

const stamp = () => `${Date.now()}-${Math.floor(Math.random() * 1000)}`;

// Which season it is depends on the real date, so these plans set every season
// the same way: the assertions then hold whenever the suite runs.
const SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter'];

test('a seasonal pace carries onto a new plant and is labelled on its reminders', async ({ page }) => {
  const id = stamp();
  const speciesName = `Sansevieria ${id}`;
  const plantName = `Snakey ${id}`;

  await page.goto('/species');
  await page.getByRole('button', { name: 'Add species' }).click();
  await page.getByPlaceholder('Monstera', { exact: true }).fill(speciesName);
  await page.getByRole('spinbutton', { name: 'Watering interval' }).fill('8');
  // The seasonal editor appears once there is a base interval to scale.
  for (const season of SEASONS) {
    await page.getByRole('spinbutton', { name: `Watering in ${season}` }).fill('21');
  }
  await page.getByRole('button', { name: 'Create species' }).click();
  await expect(page.getByText(speciesName, { exact: true })).toBeVisible();

  await page.goto('/plants/new');
  await page.getByPlaceholder('My Monstera').fill(plantName);
  await page.getByRole('combobox', { name: 'Species' }).selectOption({ label: speciesName });
  await page.getByRole('button', { name: 'Create plant' }).click();
  await expect(page.getByRole('heading', { name: plantName })).toBeVisible();

  const reminders = page.locator('section', { hasText: 'Reminders' });
  await expect(reminders.getByText('every 21 days')).toBeVisible();
  await expect(reminders.getByText(/pace/)).toBeVisible();
});

test('a reminder can be limited to a window of months', async ({ page }) => {
  const id = stamp();
  const plantName = `Repotter ${id}`;

  await page.goto('/plants/new');
  await page.getByPlaceholder('My Monstera').fill(plantName);
  await page.getByRole('button', { name: 'Create plant' }).click();
  await expect(page.getByRole('heading', { name: plantName })).toBeVisible();

  const reminders = page.locator('section', { hasText: 'Reminders' });
  await reminders.getByRole('combobox', { name: 'Event' }).selectOption('repotting');
  await reminders.getByRole('spinbutton', { name: 'Every (days)' }).fill('730');
  await reminders.getByRole('combobox', { name: 'Window start month' }).selectOption('3');
  await reminders.getByRole('combobox', { name: 'Window end month' }).selectOption('5');
  await page.getByRole('button', { name: 'Add' }).click();

  // The interval is unchanged — only the due date waits for the window.
  await expect(reminders.getByText('every 730 days')).toBeVisible();
  await expect(reminders.getByText('· in Mar–May')).toBeVisible();
});

test('pausing an event type shows it as paused instead of overdue', async ({ page }) => {
  const id = stamp();
  const speciesName = `Cyclamen ${id}`;
  const plantName = `Cycle ${id}`;

  await page.goto('/species');
  await page.getByRole('button', { name: 'Add species' }).click();
  await page.getByPlaceholder('Monstera', { exact: true }).fill(speciesName);
  await page.getByRole('spinbutton', { name: 'Fertilising interval' }).fill('30');
  for (const season of SEASONS) {
    await page.getByRole('checkbox', { name: `Pause Fertilising in ${season}` }).check();
  }
  await page.getByRole('button', { name: 'Create species' }).click();
  await expect(page.getByText(speciesName, { exact: true })).toBeVisible();

  await page.goto('/plants/new');
  await page.getByPlaceholder('My Monstera').fill(plantName);
  await page.getByRole('combobox', { name: 'Species' }).selectOption({ label: speciesName });
  await page.getByRole('button', { name: 'Create plant' }).click();
  await expect(page.getByRole('heading', { name: plantName })).toBeVisible();

  // Never fertilised, but dormant: the reminder must read as paused, not overdue.
  const reminders = page.locator('section', { hasText: 'Reminders' });
  await expect(reminders.getByText(/paused for/)).toBeVisible();
  await expect(reminders.getByText('every 30 days in season')).toBeVisible();
});
