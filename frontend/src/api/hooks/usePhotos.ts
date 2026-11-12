import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../client';
import { plantKeys, plantQueries } from '../queries';
import type { PhotoRead } from '../types';

export function usePhotos(plantId: string) {
  return useQuery(plantQueries.photos(plantId));
}

export function uploadPhoto(plantId: string, file: File): Promise<PhotoRead> {
  const form = new FormData();
  form.append('file', file);
  return api<PhotoRead>(`/api/v1/plants/${plantId}/photos`, { method: 'POST', body: form });
}

export function useUploadPhoto(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadPhoto(plantId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: plantKeys.photos(plantId) }),
  });
}

export function useDeletePhoto(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (photoId: string) => api<void>(`/api/v1/photos/${photoId}`, { method: 'DELETE' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: plantKeys.photos(plantId) });
      // The deleted photo may have been the cover, shown on the detail and the cards.
      void queryClient.invalidateQueries({ queryKey: plantKeys.detail(plantId) });
      void queryClient.invalidateQueries({ queryKey: plantKeys.lists() });
    },
  });
}
