// Central QueryClient: query and mutation errors surface as toasts by default,
// so individual pages don't need error plumbing. Two opt-outs via `meta`:
// - mutations that report their own, more specific error (errorToast: false);
// - a page's primary queries (routeError), whose first-load failure already
//   shows the route error page (the loader awaited them) and would otherwise
//   be reported twice. Background refetch failures of those still toast,
//   because the page keeps showing the stale data.

import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query';

import { notifyFromOutside } from '../components/Toast';

interface AppMeta extends Record<string, unknown> {
  errorToast?: false;
  routeError?: true;
}

declare module '@tanstack/react-query' {
  interface Register {
    queryMeta: AppMeta;
    mutationMeta: AppMeta;
  }
}

function describe(error: unknown): string {
  return error instanceof Error ? error.message : 'Unexpected error';
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.meta?.routeError && query.state.data === undefined) return;
      notifyFromOutside(describe(error));
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (mutation.meta?.errorToast === false) return;
      notifyFromOutside(describe(error));
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});
