import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import type { ReminderCreate, ReminderRead, ReminderStatusRead, ReminderUpdate } from '../types';

export function useReminders(plantId: string) {
  return useQuery({
    queryKey: ['plants', plantId, 'reminders'],
    queryFn: () => api<ReminderStatusRead[]>(`/api/v1/plants/${plantId}/reminders`),
  });
}

function invalidateReminderData(queryClient: ReturnType<typeof useQueryClient>, plantId: string): void {
  // The broad ['plants'] key also refreshes due_events on the plant cards.
  void queryClient.invalidateQueries({ queryKey: ['plants'] });
  void queryClient.invalidateQueries({ queryKey: ['plants', plantId, 'reminders'] });
  void queryClient.invalidateQueries({ queryKey: ['dashboard'] });
}

export function useCreateReminder(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReminderCreate) =>
      api<ReminderRead>(`/api/v1/plants/${plantId}/reminders`, { method: 'POST', ...jsonBody(payload) }),
    onSuccess: () => invalidateReminderData(queryClient, plantId),
  });
}

export function useUpdateReminder(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: ReminderUpdate & { id: string }) =>
      api<ReminderRead>(`/api/v1/reminders/${id}`, { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: () => invalidateReminderData(queryClient, plantId),
  });
}

export function useDeleteReminder(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/reminders/${id}`, { method: 'DELETE' }),
    onSuccess: () => invalidateReminderData(queryClient, plantId),
  });
}

// Cross-plant like useCreateLogForPlant: dashboard rows span plants, so the
// plant id rides along per call purely for cache invalidation.
export function useSnoozeReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reminderId, days }: { reminderId: string; plantId: string; days?: number }) =>
      api<ReminderRead>(`/api/v1/reminders/${reminderId}/snooze`, { method: 'POST', ...jsonBody({ days }) }),
    onSuccess: (_data, { plantId }) => invalidateReminderData(queryClient, plantId),
  });
}

export function useUnsnoozeReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reminderId }: { reminderId: string; plantId: string }) =>
      api<ReminderRead>(`/api/v1/reminders/${reminderId}/snooze`, { method: 'DELETE' }),
    onSuccess: (_data, { plantId }) => invalidateReminderData(queryClient, plantId),
  });
}
