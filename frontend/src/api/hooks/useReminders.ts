import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import type { ReminderCreate, ReminderRead, ReminderUpdate } from '../types';

export function useReminders(plantId: string) {
  return useQuery({
    queryKey: ['plants', plantId, 'reminders'],
    queryFn: () => api<ReminderRead[]>(`/api/v1/plants/${plantId}/reminders`),
  });
}

function invalidateReminderData(queryClient: ReturnType<typeof useQueryClient>, plantId: string): void {
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
