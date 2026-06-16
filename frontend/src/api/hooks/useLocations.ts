import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import type { LocationCreate, LocationRead, LocationUpdate } from '../types';

export function useLocations() {
  return useQuery({ queryKey: ['locations'], queryFn: () => api<LocationRead[]>('/api/v1/locations') });
}

export function useCreateLocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LocationCreate) =>
      api<LocationRead>('/api/v1/locations', { method: 'POST', ...jsonBody(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['locations'] }),
  });
}

export function useUpdateLocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: LocationUpdate & { id: string }) =>
      api<LocationRead>(`/api/v1/locations/${id}`, { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['locations'] }),
  });
}

export function useDeleteLocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/locations/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['locations'] });
      // Plants referencing the location lose it server-side.
      void queryClient.invalidateQueries({ queryKey: ['plants'] });
    },
  });
}
