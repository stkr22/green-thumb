import { createPlant, expect, stamp, test } from './fixtures';

test('a location can be renamed, a cancelled rename leaves no trace, and deletion keeps its plants', async ({ page }) => {
  const id = stamp();
  const original = `Hallway ${id}`;
  const renamed = `Entrance ${id}`;
  const plantName = `Pothos ${id}`;

  await page.goto('/locations');
  await page.getByLabel('New location').fill(original);
  await page.getByRole('button', { name: 'Add location' }).click();

  // A cancelled edit must not leak into the next one.
  await page.getByRole('button', { name: `Rename ${original}` }).click();
  await page.getByLabel(`New name for ${original}`).fill('Discarded');
  await page.getByRole('button', { name: 'Cancel' }).click();
  await page.getByRole('button', { name: `Rename ${original}` }).click();
  await expect(page.getByLabel(`New name for ${original}`)).toHaveValue(original);
  await page.getByLabel(`New name for ${original}`).fill(renamed);
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByText(renamed)).toBeVisible();

  await createPlant(page, plantName, { location: renamed });
  await page.goto('/locations');
  page.once('dialog', (dialog) => void dialog.accept());
  await page.getByRole('button', { name: `Delete ${renamed}` }).click();
  await expect(page.getByText(renamed)).toHaveCount(0);

  await page.goto('/plants');
  await expect(page.getByRole('link', { name: plantName })).toBeVisible();
});
