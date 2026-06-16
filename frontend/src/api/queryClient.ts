// Central QueryClient: every query/mutation error surfaces as a toast, per the
// project convention, so individual pages don't need error plumbing.

import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query';

import { notifyFromOutside } from '../components/Toast';

function describe(error: unknown): string {
  return error instanceof Error ? error.message : 'Unexpected error';
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => notifyFromOutside(describe(error)),
  }),
  mutationCache: new MutationCache({
    onError: (error) => notifyFromOutside(describe(error)),
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});
