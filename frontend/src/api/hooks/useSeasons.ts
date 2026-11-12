import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '../client';
import { dashboardKeys, plantKeys, seasonsQuery } from '../queries';
import type { SeasonPlanApplied } from '../types';

export function useSeasonInfo() {
  return useQuery(seasonsQuery);
}

export function useApplySeasonPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (speciesId: string) =>
      api<SeasonPlanApplied>(`/api/v1/species/${speciesId}/apply-season-plan`, { method: 'POST' }),
    onSuccess: () => {
      // Any plant of the species may have a new reminder pace; rare enough to
      // refresh all plant data rather than track which plants were touched.
      void queryClient.invalidateQueries({ queryKey: plantKeys.all });
      void queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
    },
  });
}
