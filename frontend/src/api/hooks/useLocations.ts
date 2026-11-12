import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import { locationKeys, locationsQuery, plantKeys } from '../queries';
import type { LocationCreate, LocationRead, LocationUpdate } from '../types';

export function useLocations() {
  return useQuery(locationsQuery);
}

export function useCreateLocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LocationCreate) =>
      api<LocationRead>('/api/v1/locations', { method: 'POST', ...jsonBody(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: locationKeys.all }),
  });
}

export function useUpdateLocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: LocationUpdate & { id: string }) =>
      api<LocationRead>(`/api/v1/locations/${id}`, { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: locationKeys.all }),
  });
}

export function useDeleteLocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/locations/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: locationKeys.all });
      // Plants in it lose their location server-side; rare enough to refresh all.
      void queryClient.invalidateQueries({ queryKey: plantKeys.all });
    },
  });
}
