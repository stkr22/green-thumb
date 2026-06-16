import { useQuery } from '@tanstack/react-query';

import { api } from '../client';
import type { DashboardSummary } from '../types';

export function useDashboard(upcomingDays = 7) {
  return useQuery({
    queryKey: ['dashboard', upcomingDays],
    queryFn: () => api<DashboardSummary>(`/api/v1/dashboard?upcoming_days=${upcomingDays}`),
  });
}
