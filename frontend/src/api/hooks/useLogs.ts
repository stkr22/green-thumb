import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import { invalidatePlantCare, plantKeys, plantQueries } from '../queries';
import type { CareLogCreate, CareLogRead, PlantDetail, PlantListItem } from '../types';

function later(a: string | null | undefined, b: string): string {
  return a && new Date(a).getTime() > new Date(b).getTime() ? a : b;
}

/**
 * Show a logged event immediately on the plant's detail ("Watered today") and
 * its card, rolling back if the request fails. The later timestamp wins: an
 * Undo re-creates an older entry, which must not move "last done" backwards.
 */
async function applyLogOptimistically(queryClient: QueryClient, plantId: string, payload: CareLogCreate) {
  const at = payload.logged_at ?? new Date().toISOString();
  const detailKey = plantKeys.detail(plantId);
  await queryClient.cancelQueries({ queryKey: detailKey });
  await queryClient.cancelQueries({ queryKey: plantKeys.lists() });
  const previousDetail = queryClient.getQueryData<PlantDetail>(detailKey);
  const previousLists = queryClient.getQueriesData<PlantListItem[]>({ queryKey: plantKeys.lists() });
  queryClient.setQueryData<PlantDetail>(detailKey, (plant) =>
    plant && {
      ...plant,
      last_events: { ...plant.last_events, [payload.event_type]: later(plant.last_events?.[payload.event_type], at) },
    },
  );
  if (payload.event_type === 'watering') {
    queryClient.setQueriesData<PlantListItem[]>({ queryKey: plantKeys.lists() }, (plants) =>
      plants?.map((plant) =>
        plant.id === plantId ? { ...plant, last_watered_at: later(plant.last_watered_at, at) } : plant,
      ),
    );
  }
  return () => {
    queryClient.setQueryData(detailKey, previousDetail);
    for (const [key, data] of previousLists) queryClient.setQueryData(key, data);
  };
}

export function useLogs(plantId: string, eventType: string | undefined, page: number) {
  return useQuery(plantQueries.logPage(plantId, eventType, page));
}

export function useJournalLogs(plantId: string) {
  return useQuery(plantQueries.journal(plantId));
}

function postLog(plantId: string, payload: CareLogCreate): Promise<CareLogRead> {
  return api<CareLogRead>(`/api/v1/plants/${plantId}/logs`, { method: 'POST', ...jsonBody(payload) });
}

export function useCreateLog(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CareLogCreate) => postLog(plantId, payload),
    onMutate: (payload) => applyLogOptimistically(queryClient, plantId, payload),
    onError: (_error, _payload, rollback) => rollback?.(),
    onSettled: () => invalidatePlantCare(queryClient, plantId),
  });
}

// Cross-plant variant for the dashboard, where each row belongs to a
// different plant so a per-plant hook instance won't do.
export function useCreateLogForPlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ plantId, ...payload }: CareLogCreate & { plantId: string }) => postLog(plantId, payload),
    onSuccess: (_data, { plantId }) => invalidatePlantCare(queryClient, plantId),
  });
}

/**
 * Log one event type for many plants at once (dashboard "Water all"). Requests
 * run in parallel and the caches refresh once at the end; returns how many
 * failed so the caller can say so.
 */
export function useCreateLogsForPlants() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ plantIds, eventType }: { plantIds: string[]; eventType: string }) => {
      const results = await Promise.allSettled(plantIds.map((id) => postLog(id, { event_type: eventType })));
      return { failed: results.filter((r) => r.status === 'rejected').length, total: plantIds.length };
    },
    onSuccess: (_data, { plantIds }) => plantIds.forEach((id) => invalidatePlantCare(queryClient, id)),
  });
}

export function useDeleteLog(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (logId: string) => api<void>(`/api/v1/logs/${logId}`, { method: 'DELETE' }),
    onSuccess: () => invalidatePlantCare(queryClient, plantId),
  });
}
