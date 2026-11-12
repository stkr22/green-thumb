import { addReminder, createPlant, expect, stamp, test } from './fixtures';

// Phone-sized layout guards. A real iPhone's focus zoom and toolbar animation
// can't be emulated here, so these pin down their causes instead: text fields
// under 16px (iOS zooms on focus, offsetting fixed elements), and a page that
// isn't the one scroll container the fixed bottom nav is anchored to.
test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

const FORM_FIELDS = 'input:not([type=checkbox]):not([type=file]):not([type=hidden]), select, textarea';

async function smallestFieldFontPx(page: import('@playwright/test').Page): Promise<number> {
  return page.locator(FORM_FIELDS).evaluateAll((fields) =>
    Math.min(...fields.map((field) => Number.parseFloat(getComputedStyle(field).fontSize))),
  );
}

test('form fields are at least 16px on phones so iOS does not zoom on focus', async ({ page }) => {
  await createPlant(page, `Zoomless ${stamp()}`);
  // Detail page: reminder form; then the list filters, the new-plant form,
  // locations and the species dialog.
  expect(await smallestFieldFontPx(page)).toBeGreaterThanOrEqual(16);
  for (const path of ['/plants', '/plants/new', '/locations', '/profile']) {
    await page.goto(path);
    await expect(page.locator(FORM_FIELDS).first()).toBeVisible();
    expect(await smallestFieldFontPx(page), path).toBeGreaterThanOrEqual(16);
  }
  await page.goto('/species');
  await page.getByRole('button', { name: 'Add species' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  expect(await smallestFieldFontPx(page), 'species dialog').toBeGreaterThanOrEqual(16);
});

test('the bottom nav stays flush with the viewport bottom while the page scrolls', async ({ page }) => {
  // A plant detail page with a reminder is comfortably taller than a phone.
  await createPlant(page, `Tall ${stamp()}`);
  await addReminder(page);

  const nav = page.getByRole('navigation', { name: 'Main' });
  const viewportHeight = page.viewportSize()!.height;
  const navBottom = async () => (await nav.boundingBox())!.y + (await nav.boundingBox())!.height;

  // The document, not <main>, must be the scroll container.
  const scroller = await page.evaluate(() => ({
    documentScrolls: document.documentElement.scrollHeight > window.innerHeight,
    mainOverflow: getComputedStyle(document.querySelector('main')!).overflowY,
  }));
  expect(scroller.documentScrolls).toBe(true);
  expect(scroller.mainOverflow).toBe('visible');

  expect(await navBottom()).toBeCloseTo(viewportHeight, 0);

  // Scroll to the true end once lazily loaded sections (photos, journal) have
  // settled; they grow the page, so an earlier "bottom" isn't the bottom.
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await expect
    .poll(() => page.evaluate(() => window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 1))
    .toBe(true);
  expect(await navBottom()).toBeCloseTo(viewportHeight, 0);

  // At the end of the page the last content must clear the nav: main's bottom
  // padding has to be at least as tall as the nav (safe-area padding included).
  const clearance = await page.evaluate(() => ({
    mainPadding: Number.parseFloat(getComputedStyle(document.querySelector('main')!).paddingBottom),
    navHeight: document.querySelector('nav[aria-label="Main"]')!.getBoundingClientRect().height,
  }));
  expect(clearance.mainPadding).toBeGreaterThanOrEqual(clearance.navHeight);
});
