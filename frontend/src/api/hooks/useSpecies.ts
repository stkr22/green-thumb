import { useQuery } from '@tanstack/react-query';

import { api } from '../client';
import type { SpeciesSearchResult } from '../types';

export function useSpeciesSearch(query: string) {
  return useQuery({
    queryKey: ['species', query],
    queryFn: () => api<SpeciesSearchResult[]>(`/api/v1/species/search?q=${encodeURIComponent(query)}`),
    enabled: query.trim().length >= 2,
    staleTime: 5 * 60_000,
  });
}
