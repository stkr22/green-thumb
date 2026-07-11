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
