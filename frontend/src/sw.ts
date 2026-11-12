// Service worker: precaches the built app shell (offline-capable UI) and
// leaves room for Web Push handlers. Data always comes from the network —
// /api and /auth are explicitly excluded from the SPA navigation fallback.

/// <reference lib="webworker" />

import { clientsClaim } from 'workbox-core';
import { createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching';
import { NavigationRoute, registerRoute } from 'workbox-routing';

declare let self: ServiceWorkerGlobalScope;

precacheAndRoute(self.__WB_MANIFEST);

registerRoute(
  new NavigationRoute(createHandlerBoundToURL('index.html'), {
    denylist: [/^\/api\//, /^\/auth\//],
  }),
);

// registerType 'autoUpdate' never messages the worker to skip waiting; it only
// reloads the page once a new worker activates. So activate and take control
// right away, otherwise an update waits until every tab and the installed PWA
// are closed.
void self.skipWaiting();
clientsClaim();

// Web Push: the backend sends {title, body} JSON (see services/webpush.py).
self.addEventListener('push', (event) => {
  let data: { title?: string; body?: string } = {};
  try {
    data = event.data?.json() ?? {};
  } catch {
    // A non-JSON payload must still show a notification: browsers penalise
    // push events that end without one.
    data = { body: event.data?.text() };
  }
  event.waitUntil(
    self.registration.showNotification(data.title ?? 'Green Thumb', {
      body: data.body ?? '',
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
      // One digest replaces the previous one instead of stacking up.
      tag: 'greenthumb-reminders',
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const open = clients.find((client): client is WindowClient => 'focus' in client);
      // The dashboard lists what's overdue, which is what the digest is about.
      // navigate() rejects for clients this worker doesn't control yet, so
      // fall back to opening a fresh window rather than doing nothing.
      if (open) return open.navigate('/').then((c) => c?.focus(), () => self.clients.openWindow('/'));
      return self.clients.openWindow('/');
    }),
  );
});
