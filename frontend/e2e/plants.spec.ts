import { addReminder, createPlant, expect, section, stamp, test, TINY_PNG } from './fixtures';

test('create a location, then a plant in it, and find it by search and tag', async ({ page }) => {
  const id = stamp();
  const locationName = `Greenhouse ${id}`;
  const plantName = `Aloe ${id}`;

  await page.goto('/locations');
  await page.getByLabel('New location').fill(locationName);
  await page.getByRole('button', { name: 'Add location' }).click();
  await expect(page.getByText(locationName)).toBeVisible();

  await createPlant(page, plantName, { location: locationName, tags: `succulent, tag-${id}` });
  await expect(page.getByText(locationName)).toBeVisible();

  await page.goto('/plants');
  await page.getByLabel('Search plants').fill(`Aloe ${id}`);
  await expect(page.getByRole('link', { name: plantName })).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(1);

  // Tag options come from all plants, so they survive the active search.
  await page.getByLabel('Search plants').fill('');
  await page.getByLabel('Filter by tag').selectOption(`tag-${id}`);
  await expect(page.getByRole('article')).toHaveCount(1);
  await expect(page.getByRole('link', { name: plantName })).toBeVisible();
});

test('editing a plant updates its page', async ({ page }) => {
  const id = stamp();
  await createPlant(page, `Draft ${id}`);

  await page.getByRole('button', { name: 'Edit' }).click();
  const dialog = page.getByRole('dialog', { name: `Edit Draft ${id}` });
  await dialog.getByLabel('Name', { exact: true }).fill(`Final ${id}`);
  await dialog.getByLabel('Notes').fill('Likes the east window');
  await dialog.getByRole('button', { name: 'Save changes' }).click();

  await expect(dialog).toBeHidden();
  await expect(page.getByRole('heading', { name: `Final ${id}`, level: 1 })).toBeVisible();
  await expect(page.getByText('Likes the east window')).toBeVisible();
});

test('the edit dialog closes with Escape and discards the draft', async ({ page }) => {
  const plantName = `Stable ${stamp()}`;
  await createPlant(page, plantName);

  await page.getByRole('button', { name: 'Edit' }).click();
  const dialog = page.getByRole('dialog', { name: `Edit ${plantName}` });
  await dialog.getByLabel('Name', { exact: true }).fill('Not saved');
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();

  await page.getByRole('button', { name: 'Edit' }).click();
  await expect(dialog.getByLabel('Name', { exact: true })).toHaveValue(plantName);
});

test('uploaded photos can become the cover', async ({ page }) => {
  const plantName = `Photogenic ${stamp()}`;
  await createPlant(page, plantName);

  const photos = section(page, 'Photos');
  await photos.getByLabel('Upload photos').setInputFiles({ name: 'leaf.png', mimeType: 'image/png', buffer: TINY_PNG });
  const setCover = photos.getByRole('button', { name: 'Set as cover photo' });
  await expect(setCover).toBeVisible();

  await setCover.click();
  await expect(photos.getByRole('button', { name: 'Current cover photo' })).toBeVisible();
  await expect(page.getByRole('img', { name: plantName })).toBeVisible();
});

test('a rejected photo still lands on the created plant instead of inviting a resubmit', async ({ page }) => {
  const plantName = `Photo ${stamp()}`;
  await page.goto('/plants/new');
  await page.getByLabel('Name', { exact: true }).fill(plantName);
  await page.getByLabel('Photo').setInputFiles({ name: 'broken.png', mimeType: 'image/png', buffer: Buffer.from('not an image') });
  await page.getByRole('button', { name: 'Create plant' }).click();

  await expect(page.getByRole('heading', { name: plantName })).toBeVisible();
  await expect(page.getByText(`${plantName} created, but the photo was not saved`)).toBeVisible();
});

test('deleting a plant leaves no trace and raises no errors', async ({ page }) => {
  const plantName = `Doomed ${stamp()}`;
  await createPlant(page, plantName);
  await addReminder(page);

  // The deleted plant's own queries must not refetch into 404s (each one would
  // surface as an error toast).
  const notFound: string[] = [];
  page.on('response', (response) => {
    if (response.status() === 404) notFound.push(response.url());
  });
  page.once('dialog', (dialog) => void dialog.accept());
  await page.getByRole('button', { name: `Delete ${plantName}` }).click();

  await expect(page).toHaveURL(/\/plants$/);
  await expect(page.getByText(`${plantName} deleted`)).toBeVisible();
  await expect(page.getByRole('link', { name: plantName })).toHaveCount(0);
  // Its reminder must be gone from the dashboard as well.
  await page.getByRole('link', { name: 'Dashboard' }).click();
  await expect(section(page, 'Overdue')).toBeVisible();
  await expect(page.getByRole('link', { name: plantName })).toHaveCount(0);
  expect(notFound).toEqual([]);
});
