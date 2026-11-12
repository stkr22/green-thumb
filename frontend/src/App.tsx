import { RouterProvider } from 'react-router/dom';

import { loginUrl } from './api/client';
import { useMe } from './api/hooks/useProfile';
import { router } from './router';

export function App() {
  // Cookie-based auth: probe the session on load. The API client redirects to
  // /auth/login on 401, so an unauthenticated visit bounces through Zitadel.
  const { data: me, isLoading, isError } = useMe();

  if (isLoading) {
    return <div className="flex min-h-dvh items-center justify-center text-stone-500">Signing you in…</div>;
  }
  if (isError || !me) {
    // The 401 redirect normally fires first; this covers network errors.
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4">
        <p className="text-stone-600">You need to sign in to manage your plants.</p>
        <a href={loginUrl()} className="btn-primary">
          Sign in
        </a>
      </div>
    );
  }

  return <RouterProvider router={router} />;
}
