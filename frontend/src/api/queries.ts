// Every query key and query definition lives here, so invalidation can name
// exactly the data a mutation changed instead of sweeping broad prefixes.
//
// Layout: plant lists and per-plant data are separate branches under 'plants',
// so "refresh the cards" never refetches every open plant's logs and photos,
// and "everything about plant X" is one prefix (plantKeys.one).

import { keepPreviousData, queryOptions, type QueryClient } from '@tanstack/react-query';

import { api, ApiError } from './client';
import type {
  CareLogRead,
  DashboardSummary,
  LocationRead,
  PhotoRead,
  PlantDetail,
  PlantListItem,
  PushPublicKey,
  ReminderStatusRead,
  SeasonInfo,
  SpeciesListItem,
  UserRead,
} from './types';

export const LOGS_PAGE_SIZE = 20;
// The journal shows the whole history; one generous page keeps it a single request.
export const JOURNAL_LOG_LIMIT = 500;

export interface PlantFilters {
  search?: string;
  locationId?: string;
  tag?: string;
}

export const plantKeys = {
  all: ['plants'] as const,
  lists: () => [...plantKeys.all, 'list'] as const,
  list: (filters: PlantFilters) => [...plantKeys.lists(), filters] as const,
  one: (plantId: string) => [...plantKeys.all, 'one', plantId] as const,
  detail: (plantId: string) => [...plantKeys.one(plantId), 'detail'] as const,
  photos: (plantId: string) => [...plantKeys.one(plantId), 'photos'] as const,
  reminders: (plantId: string) => [...plantKeys.one(plantId), 'reminders'] as const,
  logs: (plantId: string) => [...plantKeys.one(plantId), 'logs'] as const,
};

export const dashboardKeys = { all: ['dashboard'] as const };
export const speciesKeys = { all: ['species'] as const };
export const locationKeys = { all: ['locations'] as const };

export const plantQueries = {
  list: (filters: PlantFilters) => {
    const params = new URLSearchParams();
    if (filters.search) params.set('search', filters.search);
    if (filters.locationId) params.set('location_id', filters.locationId);
    if (filters.tag) params.set('tag', filters.tag);
    const query = params.toString();
    return queryOptions({
      queryKey: plantKeys.list(filters),
      queryFn: () => api<PlantListItem[]>(`/api/v1/plants${query ? `?${query}` : ''}`),
      meta: { routeError: true },
    });
  },
  detail: (plantId: string) =>
    queryOptions({
      queryKey: plantKeys.detail(plantId),
      queryFn: () => api<PlantDetail>(`/api/v1/plants/${plantId}`),
      meta: { routeError: true },
      // A missing plant stays missing; don't wait out a retry to say so.
      retry: (failureCount, error) => !(error instanceof ApiError && error.status === 404) && failureCount < 1,
    }),
  photos: (plantId: string) =>
    queryOptions({
      queryKey: plantKeys.photos(plantId),
      queryFn: () => api<PhotoRead[]>(`/api/v1/plants/${plantId}/photos`),
    }),
  reminders: (plantId: string) =>
    queryOptions({
      queryKey: plantKeys.reminders(plantId),
      queryFn: () => api<ReminderStatusRead[]>(`/api/v1/plants/${plantId}/reminders`),
    }),
  logPage: (plantId: string, eventType: string | undefined, page: number) => {
    const params = new URLSearchParams({ limit: `${LOGS_PAGE_SIZE}`, offset: `${page * LOGS_PAGE_SIZE}` });
    if (eventType) params.set('event_type', eventType);
    return queryOptions({
      queryKey: [...plantKeys.logs(plantId), 'page', { eventType, page }] as const,
      queryFn: () => api<CareLogRead[]>(`/api/v1/plants/${plantId}/logs?${params}`),
      placeholderData: keepPreviousData,
    });
  },
  journal: (plantId: string) =>
    queryOptions({
      queryKey: [...plantKeys.logs(plantId), 'journal'] as const,
      queryFn: () => api<CareLogRead[]>(`/api/v1/plants/${plantId}/logs?limit=${JOURNAL_LOG_LIMIT}`),
    }),
};

export const dashboardQuery = (upcomingDays: number) =>
  queryOptions({
    queryKey: [...dashboardKeys.all, upcomingDays] as const,
    queryFn: () => api<DashboardSummary>(`/api/v1/dashboard?upcoming_days=${upcomingDays}`),
    meta: { routeError: true },
  });

export const speciesQuery = (search: string) =>
  queryOptions({
    queryKey: [...speciesKeys.all, search] as const,
    queryFn: () =>
      api<SpeciesListItem[]>(`/api/v1/species${search ? `?search=${encodeURIComponent(search)}` : ''}`),
    meta: { routeError: true },
  });

export const locationsQuery = queryOptions({
  queryKey: locationKeys.all,
  queryFn: () => api<LocationRead[]>('/api/v1/locations'),
  meta: { routeError: true },
});

export const meQuery = queryOptions({
  queryKey: ['me'] as const,
  queryFn: () => api<UserRead>('/auth/me'),
  retry: false,
  // App renders its own sign-in screen when this fails.
  meta: { routeError: true },
});

// The hemisphere and preset table only change on redeploy, and the season only
// four times a year, so this is fetched once and kept.
export const seasonsQuery = queryOptions({
  queryKey: ['seasons'] as const,
  queryFn: () => api<SeasonInfo>('/api/v1/seasons'),
  staleTime: Infinity,
});

export const pushPublicKeyQuery = queryOptions({
  queryKey: ['push', 'public-key'] as const,
  queryFn: () => api<PushPublicKey>('/api/v1/notifications/push/public-key'),
  staleTime: Infinity, // the VAPID key never changes while deployed
});

/**
 * Refresh what a plant's care or reminder change can affect: its own detail,
 * logs and reminder statuses, the cards (last watered, due chips) and the
 * dashboard. Its photos are untouched.
 */
export function invalidatePlantCare(queryClient: QueryClient, plantId: string): void {
  void queryClient.invalidateQueries({ queryKey: plantKeys.detail(plantId) });
  void queryClient.invalidateQueries({ queryKey: plantKeys.logs(plantId) });
  void queryClient.invalidateQueries({ queryKey: plantKeys.reminders(plantId) });
  void queryClient.invalidateQueries({ queryKey: plantKeys.lists() });
  void queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
}
