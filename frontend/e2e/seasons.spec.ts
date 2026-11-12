import { createPlant, createSpecies, expect, section, stamp, test } from './fixtures';

// Which season it is depends on the real date, so these plans set every season
// the same way: the assertions then hold whenever the suite runs.
const SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter'];

test('a seasonal pace carries onto a new plant and is labelled on its reminders', async ({ page }) => {
  const id = stamp();
  const speciesName = `Sansevieria ${id}`;
  await createSpecies(page, speciesName, async (dialog) => {
    await dialog.getByRole('spinbutton', { name: 'Watering interval' }).fill('8');
    // The seasonal editor appears once there is a base interval to scale.
    for (const season of SEASONS) {
      await dialog.getByRole('spinbutton', { name: `Watering in ${season}` }).fill('21');
    }
  });
  await createPlant(page, `Snakey ${id}`, { species: speciesName });

  const reminders = section(page, 'Reminders');
  await expect(reminders.getByText('every 21 days')).toBeVisible();
  await expect(reminders.getByText(/pace/)).toBeVisible();
});

test('a reminder can be limited to a window of months', async ({ page }) => {
  await createPlant(page, `Repotter ${stamp()}`);

  const reminders = section(page, 'Reminders');
  await reminders.getByLabel('Event').selectOption('repotting');
  await reminders.getByLabel('Every (days)').fill('730');
  await reminders.getByRole('combobox', { name: 'Window start' }).selectOption('3');
  await reminders.getByRole('combobox', { name: 'Window end' }).selectOption('5');
  await reminders.getByRole('button', { name: 'Add reminder' }).click();

  // The interval is unchanged — only the due date waits for the window.
  await expect(reminders.getByText('every 730 days')).toBeVisible();
  await expect(reminders.getByText('· in Mar–May')).toBeVisible();
});

test('pausing an event type shows it as paused instead of overdue', async ({ page }) => {
  const id = stamp();
  const speciesName = `Cyclamen ${id}`;
  await createSpecies(page, speciesName, async (dialog) => {
    await dialog.getByRole('spinbutton', { name: 'Fertilising interval' }).fill('30');
    for (const season of SEASONS) {
      await dialog.getByRole('checkbox', { name: `Pause Fertilising in ${season}` }).check();
    }
  });
  await createPlant(page, `Cycle ${id}`, { species: speciesName });

  // Never fertilised, but dormant: the reminder must read as paused, not overdue.
  const reminders = section(page, 'Reminders');
  await expect(reminders.getByText(/paused for/)).toBeVisible();
  await expect(reminders.getByText('every 30 days in season')).toBeVisible();
});
