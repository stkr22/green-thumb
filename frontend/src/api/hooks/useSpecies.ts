import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import type { SpeciesCreate, SpeciesListItem, SpeciesRead, SpeciesUpdate } from '../types';

export function useSpecies(search?: string) {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  return useQuery({
    queryKey: ['species', search ?? ''],
    queryFn: () => api<SpeciesListItem[]>(`/api/v1/species${query}`),
  });
}

export function useCreateSpecies() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SpeciesCreate) =>
      api<SpeciesRead>('/api/v1/species', { method: 'POST', ...jsonBody(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['species'] }),
  });
}

export function useUpdateSpecies() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: SpeciesUpdate & { id: string }) =>
      api<SpeciesRead>(`/api/v1/species/${id}`, { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['species'] });
      // Plant detail embeds the species, so care guidance must refresh too.
      void queryClient.invalidateQueries({ queryKey: ['plants'] });
    },
  });
}

export function useDeleteSpecies() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/species/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['species'] });
      // Plants referencing the species lose it server-side.
      void queryClient.invalidateQueries({ queryKey: ['plants'] });
    },
  });
}
