import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../client';
import type { PhotoRead } from '../types';

export function usePhotos(plantId: string) {
  return useQuery({
    queryKey: ['plants', plantId, 'photos'],
    queryFn: () => api<PhotoRead[]>(`/api/v1/plants/${plantId}/photos`),
  });
}

export function useUploadPhoto(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return api<PhotoRead>(`/api/v1/plants/${plantId}/photos`, { method: 'POST', body: form });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plants', plantId, 'photos'] }),
  });
}

export function useDeletePhoto(plantId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (photoId: string) => api<void>(`/api/v1/photos/${photoId}`, { method: 'DELETE' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['plants', plantId, 'photos'] });
      // The deleted photo may have been the cover.
      void queryClient.invalidateQueries({ queryKey: ['plants'] });
    },
  });
}
