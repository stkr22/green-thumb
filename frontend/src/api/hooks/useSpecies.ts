import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import { plantKeys, speciesKeys, speciesQuery } from '../queries';
import type { SpeciesCreate, SpeciesRead, SpeciesUpdate } from '../types';

export function useSpecies(search = '') {
  return useQuery(speciesQuery(search));
}

export function useCreateSpecies() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SpeciesCreate) =>
      api<SpeciesRead>('/api/v1/species', { method: 'POST', ...jsonBody(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: speciesKeys.all }),
  });
}

export function useUpdateSpecies() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: SpeciesUpdate & { id: string }) =>
      api<SpeciesRead>(`/api/v1/species/${id}`, { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: speciesKeys.all });
      // Plant details embed the species and cards show its name; species edits
      // are rare, so refreshing all plant data is cheaper than tracking plants.
      void queryClient.invalidateQueries({ queryKey: plantKeys.all });
    },
  });
}

export function useDeleteSpecies() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/api/v1/species/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: speciesKeys.all });
      // Plants referencing the species lose it server-side.
      void queryClient.invalidateQueries({ queryKey: plantKeys.all });
    },
  });
}
