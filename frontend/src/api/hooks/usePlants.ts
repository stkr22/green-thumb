import { useMutation, useQueryClient, useSuspenseQuery } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import { dashboardKeys, plantKeys, plantQueries, type PlantFilters } from '../queries';
import type { PlantCreate, PlantRead, PlantUpdate, ReminderRead } from '../types';

export type { PlantFilters };

// Suspense: only route pages call these, and their loaders await the data, so
// the pages get it without loading or error branches (errors reach RouteError).
export function usePlants(filters: PlantFilters = {}) {
  return useSuspenseQuery(plantQueries.list(filters));
}

export function usePlant(plantId: string) {
  return useSuspenseQuery(plantQueries.detail(plantId));
}

export function useCreatePlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PlantCreate) => api<PlantRead>('/api/v1/plants', { method: 'POST', ...jsonBody(payload) }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: plantKeys.lists() });
      // Species defaults may have created reminders that are already due.
      void queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useUpdatePlant(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PlantUpdate) =>
      api<PlantRead>(`/api/v1/plants/${plantId}`, { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: plantKeys.detail(plantId) });
      void queryClient.invalidateQueries({ queryKey: plantKeys.lists() });
      // The dashboard shows plant names.
      void queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useDeletePlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (plantId: string) => api<void>(`/api/v1/plants/${plantId}`, { method: 'DELETE' }),
    onSuccess: () => {
      // The deleted plant's own queries (plantKeys.one) are deliberately left
      // alone: refetching them while its page is still mounted turns each into
      // a 404 error toast. Once the caller navigates away they're
      // garbage-collected. Not awaited, so that navigation happens at once.
      void queryClient.invalidateQueries({ queryKey: plantKeys.lists() });
      void queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useApplySpeciesDefaults(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<ReminderRead[]>(`/api/v1/plants/${plantId}/apply-species-defaults`, { method: 'POST' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: plantKeys.reminders(plantId) });
      void queryClient.invalidateQueries({ queryKey: plantKeys.lists() });
      void queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}

export function useSetCoverPhoto(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (photoId: string) =>
      api<PlantRead>(`/api/v1/plants/${plantId}/cover`, { method: 'POST', ...jsonBody({ photo_id: photoId }) }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: plantKeys.detail(plantId) });
      void queryClient.invalidateQueries({ queryKey: plantKeys.lists() });
    },
  });
}
