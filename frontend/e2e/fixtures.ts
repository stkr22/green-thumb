// Shared e2e helpers. Specs share one SQLite file, so every entity gets a
// unique name; selectors go through labels and roles, so they break when
// accessibility does rather than when markup moves.

import { expect, type Locator, type Page } from '@playwright/test';

export { expect, test } from '@playwright/test';

/** Unique suffix per call so tests don't collide with each other or earlier runs. */
export const stamp = () => `${Date.now()}-${Math.floor(Math.random() * 1000)}`;

/** A page section identified by its heading, not by text it happens to contain. */
export function section(page: Page, heading: string | RegExp): Locator {
  return page.locator('section').filter({ has: page.getByRole('heading', { name: heading, exact: true }) });
}

export async function createPlant(
  page: Page,
  name: string,
  options: { species?: string; location?: string; tags?: string } = {},
): Promise<void> {
  await page.goto('/plants/new');
  await page.getByLabel('Name', { exact: true }).fill(name);
  if (options.species) await page.getByLabel('Species', { exact: true }).selectOption({ label: options.species });
  if (options.location) await page.getByLabel('Location').selectOption({ label: options.location });
  if (options.tags) await page.getByLabel('Tags (comma-separated)').fill(options.tags);
  await page.getByRole('button', { name: 'Create plant' }).click();
  await expect(page.getByRole('heading', { name, level: 1 })).toBeVisible();
}

/** Opens "Add species", fills the name, lets the caller fill the rest, then saves. */
export async function createSpecies(page: Page, name: string, fill?: (dialog: Locator) => Promise<void>) {
  await page.goto('/species');
  await page.getByRole('button', { name: 'Add species' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add species' });
  await dialog.getByLabel('Name', { exact: true }).fill(name);
  await fill?.(dialog);
  await dialog.getByRole('button', { name: 'Create species' }).click();
  await expect(page.getByText(name, { exact: true })).toBeVisible();
}

/** Adds a reminder on the current plant page; defaults to watering every 7 days. */
export async function addReminder(page: Page, options: { event?: string; days?: number } = {}) {
  const reminders = section(page, 'Reminders');
  if (options.event) await reminders.getByLabel('Event').selectOption(options.event);
  if (options.days) await reminders.getByLabel('Every (days)').fill(String(options.days));
  await reminders.getByRole('button', { name: 'Add reminder' }).click();
  await expect(reminders.getByRole('list', { name: 'Reminders' })).toBeVisible();
}

/** A 1x1 PNG, enough for the backend's decode + re-encode pipeline. */
export const TINY_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64',
);
