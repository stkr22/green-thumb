import { createPlant, createSpecies, expect, section, stamp, test } from './fixtures';

test('species with a default care plan seeds a new plant with reminders', async ({ page }) => {
  const id = stamp();
  const speciesName = `Monstera ${id}`;
  const plantName = `Monsti ${id}`;

  await createSpecies(page, speciesName, async (dialog) => {
    await dialog.getByLabel('Light').fill('Bright indirect light');
    await dialog.getByRole('spinbutton', { name: 'Watering interval' }).fill('7');
  });
  await expect(page.getByText('watering every 7d')).toBeVisible();

  // A plant linked to the species inherits the care plan and shows the guide.
  await createPlant(page, plantName, { species: speciesName });
  await expect(section(page, /^Care guide/).getByText('Bright indirect light')).toBeVisible();
  await expect(section(page, 'Reminders').getByText('every 7 days')).toBeVisible();
});

test('an invalid default interval is reported inline', async ({ page }) => {
  await page.goto('/species');
  await page.getByRole('button', { name: 'Add species' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add species' });
  await dialog.getByLabel('Name', { exact: true }).fill(`Typo ${stamp()}`);
  await dialog.getByRole('spinbutton', { name: 'Watering interval' }).fill('-3');
  await dialog.getByRole('button', { name: 'Create species' }).click();

  await expect(dialog.getByText('Enter 1–3650 days, or leave empty')).toBeVisible();
  await expect(dialog).toBeVisible();
});

test('a changed pace can be applied to existing plants of the species', async ({ page }) => {
  const id = stamp();
  const speciesName = `Calathea ${id}`;
  const plantName = `Cally ${id}`;

  await createSpecies(page, speciesName, async (dialog) => {
    await dialog.getByRole('spinbutton', { name: 'Watering interval' }).fill('10');
  });
  await createPlant(page, plantName, { species: speciesName });
  await expect(section(page, 'Reminders').getByText('every 10 days')).toBeVisible();

  // Every season the same, so the assertion holds whatever today's season is.
  await page.goto('/species');
  await page.getByRole('button', { name: `Edit ${speciesName}` }).click();
  const dialog = page.getByRole('dialog', { name: `Edit ${speciesName}` });
  for (const season of ['Spring', 'Summer', 'Autumn', 'Winter']) {
    await dialog.getByRole('spinbutton', { name: `Watering in ${season}` }).fill('20');
  }
  await dialog.getByRole('button', { name: 'Save changes' }).click();
  await page.getByRole('button', { name: 'Apply pace to existing plants' }).click();
  await expect(page.getByText(/^Seasonal pace applied to 1 reminder$/)).toBeVisible();

  await page.getByRole('link', { name: 'Plants', exact: true }).click();
  await page.getByRole('link', { name: plantName }).click();
  await expect(section(page, 'Reminders').getByText('every 20 days')).toBeVisible();
});
