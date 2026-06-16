import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, jsonBody } from '../client';
import type { PlantCreate, PlantDetail, PlantListItem, PlantRead, PlantUpdate } from '../types';

export interface PlantFilters {
  search?: string;
  locationId?: string;
  tag?: string;
}

export function usePlants(filters: PlantFilters = {}) {
  const params = new URLSearchParams();
  if (filters.search) params.set('search', filters.search);
  if (filters.locationId) params.set('location_id', filters.locationId);
  if (filters.tag) params.set('tag', filters.tag);
  const query = params.toString();
  return useQuery({
    queryKey: ['plants', filters],
    queryFn: () => api<PlantListItem[]>(`/api/v1/plants${query ? `?${query}` : ''}`),
  });
}

export function usePlant(plantId: string) {
  return useQuery({
    queryKey: ['plants', plantId],
    queryFn: () => api<PlantDetail>(`/api/v1/plants/${plantId}`),
  });
}

export function useCreatePlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PlantCreate) => api<PlantRead>('/api/v1/plants', { method: 'POST', ...jsonBody(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plants'] }),
  });
}

export function useUpdatePlant(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PlantUpdate) =>
      api<PlantRead>(`/api/v1/plants/${plantId}`, { method: 'PATCH', ...jsonBody(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plants'] }),
  });
}

export function useDeletePlant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (plantId: string) => api<void>(`/api/v1/plants/${plantId}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plants'] }),
  });
}

export function useSetCoverPhoto(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (photoId: string) =>
      api<PlantRead>(`/api/v1/plants/${plantId}/cover`, { method: 'POST', ...jsonBody({ photo_id: photoId }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plants'] }),
  });
}
