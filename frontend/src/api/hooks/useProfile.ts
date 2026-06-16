import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import type { UserRead, UserUpdate } from '../types';

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => api<UserRead>('/auth/me'), retry: false });
}

export function useUpdateMe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UserUpdate) => api<UserRead>('/auth/me', { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: (me) => queryClient.setQueryData(['me'], me),
  });
}

export function useTestNotification() {
  return useMutation({
    mutationFn: () => api<{ detail: string }>('/api/v1/notifications/test', { method: 'POST' }),
  });
}
