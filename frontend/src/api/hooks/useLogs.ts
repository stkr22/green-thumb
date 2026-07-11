import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import type { CareLogCreate, CareLogRead } from '../types';

const PAGE_SIZE = 20;

export function useLogs(plantId: string, eventType: string | undefined, page: number) {
  const params = new URLSearchParams({ limit: `${PAGE_SIZE}`, offset: `${page * PAGE_SIZE}` });
  if (eventType) params.set('event_type', eventType);
  return useQuery({
    queryKey: ['plants', plantId, 'logs', { eventType, page }],
    queryFn: () => api<CareLogRead[]>(`/api/v1/plants/${plantId}/logs?${params}`),
  });
}

export const LOGS_PAGE_SIZE = PAGE_SIZE;

function invalidateCareData(queryClient: ReturnType<typeof useQueryClient>, plantId: string): void {
  // Care logs feed the plant detail (last events), list (last watered) and dashboard.
  void queryClient.invalidateQueries({ queryKey: ['plants'] });
  void queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  void queryClient.invalidateQueries({ queryKey: ['plants', plantId, 'logs'] });
}

export function useCreateLog(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CareLogCreate) =>
      api<CareLogRead>(`/api/v1/plants/${plantId}/logs`, { method: 'POST', ...jsonBody(payload) }),
    onSuccess: () => invalidateCareData(queryClient, plantId),
  });
}

// Cross-plant variant for the dashboard, where each row belongs to a
// different plant so a per-plant hook instance won't do.
export function useCreateLogForPlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ plantId, ...payload }: CareLogCreate & { plantId: string }) =>
      api<CareLogRead>(`/api/v1/plants/${plantId}/logs`, { method: 'POST', ...jsonBody(payload) }),
    onSuccess: (_data, { plantId }) => invalidateCareData(queryClient, plantId),
  });
}

export function useDeleteLog(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (logId: string) => api<void>(`/api/v1/logs/${logId}`, { method: 'DELETE' }),
    onSuccess: () => invalidateCareData(queryClient, plantId),
  });
}
