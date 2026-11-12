import { useSuspenseQuery } from '@tanstack/react-query';

import { dashboardQuery } from '../queries';

// Suspense: only route pages call this, and their loaders await the data.
export function useDashboard(upcomingDays = 7) {
  return useSuspenseQuery(dashboardQuery(upcomingDays));
}
