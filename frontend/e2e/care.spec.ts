import { addReminder, createPlant, expect, section, stamp, test } from './fixtures';

test('logging care updates the summary and timeline, and Undo reverts it', async ({ page }) => {
  await createPlant(page, `Fern ${stamp()}`);

  const waterCard = page.getByRole('button', { name: /^Water\b/ });
  await expect(waterCard.getByText('Watered never')).toBeVisible();

  await waterCard.click();
  await expect(waterCard.getByText('Watered today')).toBeVisible();
  const careLog = section(page, 'Care log');
  await expect(careLog.getByRole('listitem').filter({ hasText: /watering/i })).toBeVisible();

  await page.getByRole('button', { name: 'Undo' }).click();
  await expect(waterCard.getByText('Watered never')).toBeVisible();
  await expect(careLog.getByText('No care events logged yet.')).toBeVisible();
});

test('a custom care event can be logged with notes', async ({ page }) => {
  await createPlant(page, `Orchid ${stamp()}`);

  await page.getByRole('button', { name: 'Custom' }).click();
  const dialog = page.getByRole('dialog', { name: 'Log custom care event' });
  await dialog.getByLabel('Event type').fill('misting');
  await dialog.getByLabel('Notes (optional)').fill('Leaves looked dry');
  await dialog.getByRole('button', { name: 'Log event' }).click();

  await expect(dialog).toBeHidden();
  const careLog = section(page, 'Care log');
  await expect(careLog.getByText('Leaves looked dry')).toBeVisible();
});

test('a due reminder flags the card, sits in Overdue, and snoozing moves it to upcoming', async ({ page }) => {
  const plantName = `Basil ${stamp()}`;
  await createPlant(page, plantName);
  // A watering reminder without any care log is immediately due.
  await addReminder(page);

  await page.goto('/plants');
  const card = page.getByRole('article').filter({ has: page.getByRole('link', { name: plantName }) });
  await expect(card.getByText('Water due')).toBeVisible();

  await page.goto('/');
  const overdue = page.getByRole('list', { name: 'Overdue reminders' });
  const row = overdue.getByRole('listitem').filter({ hasText: plantName });
  await expect(row).toBeVisible();

  await row.getByTitle(/^Snooze watering/).click();
  await expect(page.getByText(/watering snoozed for 7 days/)).toBeVisible();

  // Gone from Overdue; parked in the upcoming list labelled as snoozed.
  await expect(overdue.getByRole('listitem').filter({ hasText: plantName })).toHaveCount(0);
  const snoozedRow = page.getByRole('list', { name: 'Upcoming reminders' }).getByRole('listitem').filter({ hasText: plantName });
  await expect(snoozedRow.getByText('snoozed')).toBeVisible();
});

test('Water all logs every overdue plant at once', async ({ page }) => {
  const id = stamp();
  for (const name of [`Thirsty A ${id}`, `Thirsty B ${id}`]) {
    await createPlant(page, name);
    await addReminder(page);
  }

  await page.goto('/');
  await page.getByRole('button', { name: /^Water all/ }).click();
  await expect(page.getByText(/^Watering logged for \d+ plants$/)).toBeVisible();
  const overdue = section(page, 'Overdue');
  await expect(overdue.getByText(`Thirsty A ${id}`)).toHaveCount(0);
  await expect(overdue.getByText(`Thirsty B ${id}`)).toHaveCount(0);
});

test('the calendar lists overdue care on today', async ({ page }) => {
  const plantName = `Calendula ${stamp()}`;
  await createPlant(page, plantName);
  await addReminder(page);

  await page.goto('/calendar');
  // Today is selected by default, and overdue reminders are pinned to it.
  await expect(page.getByRole('heading', { name: /^Due on / })).toBeVisible();
  await expect(page.getByRole('link', { name: new RegExp(plantName) })).toBeVisible();
});
