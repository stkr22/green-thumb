// Data router with one lazily loaded chunk per page, so the first visit only
// downloads the dashboard.
//
// Each loader awaits the page's *primary* data (ensureQueryData) in parallel
// with the chunk download, so a page renders complete: no loading branch, and
// a failed or missing resource lands on the route error page instead of a
// half-drawn screen. While that happens the previous page stays visible under
// the progress bar (see Layout). Cached data, even stale, resolves at once and
// is refreshed in the background. Secondary data (photos, reminders) is only
// prefetched, so it never holds up navigation.

import { createBrowserRouter, type LoaderFunctionArgs } from 'react-router';

import {
  dashboardQuery,
  locationsQuery,
  plantQueries,
  pushPublicKeyQuery,
  speciesQuery,
} from './api/queries';
import { queryClient } from './api/queryClient';
import { Layout } from './components/Layout';
import { NotFoundPage, RouteError, type RouteHandle } from './components/RouteError';
import { PageSkeleton } from './components/Skeleton';
import { horizonToEndOfMonth } from './lib/dates';

/** Resolves with cached data (even stale, refreshed in the background) or fetches it. */
const load: typeof queryClient.ensureQueryData = (options) =>
  queryClient.ensureQueryData({ ...options, revalidateIfStale: true });

/** A loader result once all of a page's primary queries have data. */
async function ensure(...loads: Promise<unknown>[]): Promise<null> {
  await Promise.all(loads);
  return null;
}

// prefetchQuery never rejects; its promise is deliberately not awaited.
const prefetch = queryClient.prefetchQuery.bind(queryClient);

export const router = createBrowserRouter([
  {
    Component: Layout,
    // Shown only for the very first load, before any page exists to keep on screen.
    HydrateFallback: PageSkeleton,
    children: [
      {
        // Inside the layout so the navigation stays usable when one page fails.
        errorElement: <RouteError />,
        children: [
          {
            path: '/',
            loader: () => ensure(load(dashboardQuery(7))),
            lazy: () => import('./pages/DashboardPage').then((m) => ({ Component: m.DashboardPage })),
          },
          {
            path: '/plants',
            loader: () => ensure(load(plantQueries.list({})), load(locationsQuery)),
            lazy: () => import('./pages/PlantsPage').then((m) => ({ Component: m.PlantsPage })),
          },
          {
            path: '/plants/new',
            // The form's selects should be populated when it appears.
            loader: () => ensure(load(locationsQuery), load(speciesQuery(''))),
            lazy: () => import('./pages/PlantNewPage').then((m) => ({ Component: m.PlantNewPage })),
          },
          {
            path: '/plants/:id',
            handle: { what: 'plant', backTo: { to: '/plants', label: 'All plants' } } satisfies RouteHandle,
            loader: ({ params }: LoaderFunctionArgs) => {
              const id = params.id ?? '';
              void prefetch(plantQueries.reminders(id));
              void prefetch(plantQueries.photos(id));
              return ensure(load(plantQueries.detail(id)), load(locationsQuery));
            },
            lazy: () => import('./pages/PlantDetailPage').then((m) => ({ Component: m.PlantDetailPage })),
          },
          {
            path: '/locations',
            loader: () => ensure(load(locationsQuery)),
            lazy: () => import('./pages/LocationsPage').then((m) => ({ Component: m.LocationsPage })),
          },
          {
            path: '/species',
            loader: () => ensure(load(speciesQuery(''))),
            lazy: () => import('./pages/SpeciesPage').then((m) => ({ Component: m.SpeciesPage })),
          },
          {
            path: '/calendar',
            loader: () => {
              const today = new Date();
              return ensure(load(dashboardQuery(horizonToEndOfMonth(today.getFullYear(), today.getMonth()))));
            },
            lazy: () => import('./pages/CalendarPage').then((m) => ({ Component: m.CalendarPage })),
          },
          {
            path: '/profile',
            loader: () => {
              void prefetch(pushPublicKeyQuery);
              return null;
            },
            lazy: () => import('./pages/ProfilePage').then((m) => ({ Component: m.ProfilePage })),
          },
          { path: '*', Component: NotFoundPage },
        ],
      },
    ],
  },
]);
