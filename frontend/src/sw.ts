// Service worker: precaches the built app shell (offline-capable UI) and
// leaves room for Web Push handlers. Data always comes from the network —
// /api and /auth are explicitly excluded from the SPA navigation fallback.

/// <reference lib="webworker" />

import { createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching';
import { NavigationRoute, registerRoute } from 'workbox-routing';

declare let self: ServiceWorkerGlobalScope;

precacheAndRoute(self.__WB_MANIFEST);

registerRoute(
  new NavigationRoute(createHandlerBoundToURL('index.html'), {
    denylist: [/^\/api\//, /^\/auth\//],
  }),
);

// Take over immediately on update so users aren't stuck on a stale shell.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') void self.skipWaiting();
});

// Web Push: the backend sends {title, body} JSON (see services/webpush.py).
self.addEventListener('push', (event) => {
  const data = (event.data?.json() ?? {}) as { title?: string; body?: string };
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
      if (open) return open.navigate('/').then((c) => c?.focus());
      return self.clients.openWindow('/');
    }),
  );
});
