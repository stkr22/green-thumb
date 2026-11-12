import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import { dashboardKeys, invalidatePlantCare, plantKeys, plantQueries } from '../queries';
import type { DashboardSummary, ReminderCreate, ReminderRead, ReminderStatusRead, ReminderUpdate } from '../types';
import { snoozeDays } from '../../lib/reminders';

const DAY_MS = 24 * 60 * 60 * 1000;

type SnoozedUntil = (reminder: { interval_days: number; effective_interval_days?: number | null }) => string | null;

/**
 * Patch one reminder's snooze state wherever it is cached (the plant's
 * reminder list and every dashboard horizon) so the row flips at once.
 * Returns a rollback for onError.
 */
async function patchSnoozeOptimistically(queryClient: QueryClient, plantId: string, reminderId: string, until: SnoozedUntil) {
  const remindersKey = plantKeys.reminders(plantId);
  await queryClient.cancelQueries({ queryKey: remindersKey });
  await queryClient.cancelQueries({ queryKey: dashboardKeys.all });
  const previousReminders = queryClient.getQueryData<ReminderStatusRead[]>(remindersKey);
  const previousDashboards = queryClient.getQueriesData<DashboardSummary>({ queryKey: dashboardKeys.all });

  queryClient.setQueryData<ReminderStatusRead[]>(remindersKey, (reminders) =>
    reminders?.map((r) => (r.id === reminderId ? { ...r, snoozed_until: until(r) } : r)),
  );
  queryClient.setQueriesData<DashboardSummary>({ queryKey: dashboardKeys.all }, (summary) => {
    if (!summary) return summary;
    const patch = (list: DashboardSummary['overdue']) =>
      list.map((s) => (s.reminder_id === reminderId ? { ...s, snoozed_until: until(s) } : s));
    return { ...summary, overdue: patch(summary.overdue), upcoming: patch(summary.upcoming) };
  });

  return () => {
    queryClient.setQueryData(remindersKey, previousReminders);
    for (const [key, data] of previousDashboards) queryClient.setQueryData(key, data);
  };
}

export function useReminders(plantId: string) {
  return useQuery(plantQueries.reminders(plantId));
}

export function useCreateReminder(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReminderCreate) =>
      api<ReminderRead>(`/api/v1/plants/${plantId}/reminders`, { method: 'POST', ...jsonBody(payload) }),
    onSuccess: () => invalidatePlantCare(queryClient, plantId),
  });
}

export function useUpdateReminder(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: ReminderUpdate & { id: string }) =>
      api<ReminderRead>(`/api/v1/reminders/${id}`, { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: () => invalidatePlantCare(queryClient, plantId),
  });
}

export function useDeleteReminder(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/reminders/${id}`, { method: 'DELETE' }),
    onSuccess: () => invalidatePlantCare(queryClient, plantId),
  });
}

// Cross-plant like useCreateLogForPlant: dashboard rows span plants, so the
// plant id rides along per call purely for cache invalidation.
export function useSnoozeReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reminderId, days }: { reminderId: string; plantId: string; days?: number }) =>
      api<ReminderRead>(`/api/v1/reminders/${reminderId}/snooze`, { method: 'POST', ...jsonBody({ days }) }),
    // Without explicit days the server defers by the reminder's current pace.
    onMutate: ({ reminderId, plantId, days }) =>
      patchSnoozeOptimistically(queryClient, plantId, reminderId, (r) =>
        new Date(Date.now() + (days ?? snoozeDays(r)) * DAY_MS).toISOString(),
      ),
    onError: (_error, _variables, rollback) => rollback?.(),
    onSettled: (_data, _error, { plantId }) => invalidatePlantCare(queryClient, plantId),
  });
}

export function useUnsnoozeReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reminderId }: { reminderId: string; plantId: string }) =>
      api<ReminderRead>(`/api/v1/reminders/${reminderId}/snooze`, { method: 'DELETE' }),
    onMutate: ({ reminderId, plantId }) => patchSnoozeOptimistically(queryClient, plantId, reminderId, () => null),
    onError: (_error, _variables, rollback) => rollback?.(),
    onSettled: (_data, _error, { plantId }) => invalidatePlantCare(queryClient, plantId),
  });
}
