import { expect, test } from './fixtures';

// Headless Chromium has no push service and the Vite dev server registers no
// service worker, so stand in for both: a fake PushManager that remembers its
// subscription across reloads (like a real one) and reports the VAPID key it
// was created with. Everything above it — permission, server registration,
// reconciliation on load, unsubscribe — is the real app against the real API.
async function fakePushService(page: import('@playwright/test').Page) {
  await page.context().grantPermissions(['notifications']);
  await page.addInitScript(() => {
    const STORE = 'fake-push-subscription';
    const asSubscription = (stored: { endpoint: string; key: number[] }) => ({
      endpoint: stored.endpoint,
      options: { applicationServerKey: new Uint8Array(stored.key).buffer },
      toJSON: () => ({ endpoint: stored.endpoint, keys: { p256dh: 'fake-p256dh', auth: 'fake-auth' } }),
      unsubscribe: async () => {
        localStorage.removeItem(STORE);
        return true;
      },
    });
    const pushManager = {
      getSubscription: async () => {
        const raw = localStorage.getItem(STORE);
        return raw ? asSubscription(JSON.parse(raw)) : null;
      },
      subscribe: async ({ applicationServerKey }: { applicationServerKey: Uint8Array }) => {
        const stored = { endpoint: `https://push.example/${Date.now()}`, key: [...applicationServerKey] };
        localStorage.setItem(STORE, JSON.stringify(stored));
        return asSubscription(stored);
      },
    };
    Object.defineProperty(navigator.serviceWorker, 'ready', { value: Promise.resolve({ pushManager }) });
  });
}

test('push notifications can be enabled, survive a reload, and be disabled', async ({ page }) => {
  await fakePushService(page);
  await page.goto('/profile');

  await page.getByRole('button', { name: 'Enable on this device' }).click();
  await expect(page.getByText('Push notifications enabled on this device')).toBeVisible();

  // On load the subscription is checked against the server's key and re-registered.
  await page.reload();
  await expect(page.getByRole('button', { name: 'Disable on this device' })).toBeVisible();

  await page.getByRole('button', { name: 'Disable on this device' }).click();
  await expect(page.getByRole('button', { name: 'Enable on this device' })).toBeVisible();
});

test('the ntfy topic override is saved and shown after a reload', async ({ page }) => {
  await page.goto('/profile');
  await page.getByLabel('ntfy topic override').fill('my-e2e-topic');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByText('Notification settings saved')).toBeVisible();

  await page.reload();
  await expect(page.getByLabel('ntfy topic override')).toHaveValue('my-e2e-topic');
  await page.getByLabel('ntfy topic override').fill('');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
});
