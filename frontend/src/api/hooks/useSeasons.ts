import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../client';
import type { SeasonInfo, SeasonPlanApplied } from '../types';

// The hemisphere and the preset table only change on redeploy, and the season
// only changes four times a year, so this is fetched once and kept.
export function useSeasonInfo() {
  return useQuery({
    queryKey: ['seasons'],
    queryFn: () => api<SeasonInfo>('/api/v1/seasons'),
    staleTime: Infinity,
  });
}

export function useApplySeasonPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (speciesId: string) =>
      api<SeasonPlanApplied>(`/api/v1/species/${speciesId}/apply-season-plan`, { method: 'POST' }),
    onSuccess: () => {
      // Every plant's reminder pace may have moved.
      void queryClient.invalidateQueries({ queryKey: ['reminders'] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      void queryClient.invalidateQueries({ queryKey: ['plants'] });
    },
  });
}
