import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import { meQuery } from '../queries';
import type { ApiTokenRead, UserRead, UserUpdate } from '../types';

export function useMe() {
  return useQuery(meQuery);
}

export function useUpdateMe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UserUpdate) => api<UserRead>('/auth/me', { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: (me) => queryClient.setQueryData(meQuery.queryKey, me),
  });
}

export function useTestNotification() {
  return useMutation({
    mutationFn: () => api<{ detail: string }>('/api/v1/notifications/test', { method: 'POST' }),
  });
}

export function useMintApiToken() {
  return useMutation({
    mutationFn: () => api<ApiTokenRead>('/auth/api-token', { method: 'POST' }),
  });
}
