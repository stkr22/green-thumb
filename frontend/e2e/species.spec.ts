import { test, expect } from '@playwright/test';

const stamp = () => `${Date.now()}-${Math.floor(Math.random() * 1000)}`;

test('species with a default care plan seeds a new plant with reminders', async ({ page }) => {
  const id = stamp();
  const speciesName = `Monstera ${id}`;
  const plantName = `Monsti ${id}`;

  // Create a species with care advice and a default watering interval.
  await page.goto('/species');
  await page.getByRole('button', { name: 'Add species' }).click();
  await page.getByPlaceholder('Monstera', { exact: true }).fill(speciesName);
  await page.getByPlaceholder('Bright indirect').fill('Bright indirect light');
  await page.getByRole('spinbutton', { name: 'Watering interval' }).fill('7');
  await page.getByRole('button', { name: 'Create species' }).click();
  await expect(page.getByText(speciesName, { exact: true })).toBeVisible();
  await expect(page.getByText('watering every 7d')).toBeVisible();

  // A plant linked to the species inherits the care plan and shows the guide.
  await page.goto('/plants/new');
  await page.getByPlaceholder('My Monstera').fill(plantName);
  await page.getByRole('combobox', { name: 'Species' }).selectOption({ label: speciesName });
  await page.getByRole('button', { name: 'Create plant' }).click();
  await expect(page.getByRole('heading', { name: plantName })).toBeVisible();

  const careGuide = page.locator('section', { hasText: 'Care guide' });
  await expect(careGuide.getByText('Bright indirect light')).toBeVisible();
  const reminders = page.locator('section', { hasText: 'Reminders' });
  await expect(reminders.getByText('every 7 days')).toBeVisible();
});
