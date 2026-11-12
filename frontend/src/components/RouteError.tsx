// Route-level error page: loaders await each page's primary data, so a failed
// or missing resource lands here rather than in a half-rendered page. Also
// catches the classic post-deploy failure, a stale tab asking for a lazy chunk
// whose hashed filename no longer exists, which only a reload can fix.

import { isRouteErrorResponse, Link, useMatches, useRevalidator, useRouteError } from 'react-router';
import { RefreshCw, SearchX, TriangleAlert } from 'lucide-react';

import { ApiError } from '../api/client';

/** Per-route wording for this page, set via the route's `handle`. */
export interface RouteHandle {
  /** What the route shows, e.g. "plant"; used in the not-found message. */
  what: string;
  backTo?: { to: string; label: string };
}

function isChunkLoadError(error: unknown): boolean {
  return error instanceof TypeError && /dynamically imported module|Importing a module script failed/i.test(error.message);
}

export function RouteError() {
  const error = useRouteError();
  const revalidator = useRevalidator();
  const handle = useMatches().at(-1)?.handle as RouteHandle | undefined;
  const what = handle?.what ?? 'page';
  const notFound = (error instanceof ApiError || isRouteErrorResponse(error)) && error.status === 404;
  const staleBuild = isChunkLoadError(error);

  return (
    <div role="alert" className="card mx-auto mt-16 flex max-w-md flex-col items-center gap-3 p-8 text-center">
      {notFound ? <SearchX className="h-10 w-10 text-stone-400" /> : <TriangleAlert className="h-10 w-10 text-amber-500" />}
      <p className="font-medium">
        {notFound
          ? `This ${what} doesn't exist (any more).`
          : staleBuild
            ? 'A new version of Green Thumb is available.'
            : `Couldn't load this ${what}.`}
      </p>
      {!notFound && !staleBuild && error instanceof Error && <p className="text-sm text-stone-500">{error.message}</p>}
      <div className="flex gap-2">
        {staleBuild ? (
          <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
            <RefreshCw className="h-4 w-4" />
            Reload
          </button>
        ) : (
          !notFound && (
            // Re-runs the loaders; on success the page replaces this one.
            <button
              type="button"
              className="btn-primary"
              disabled={revalidator.state === 'loading'}
              onClick={() => void revalidator.revalidate()}
            >
              <RefreshCw className="h-4 w-4" />
              Try again
            </button>
          )
        )}
        <Link to={handle?.backTo?.to ?? '/'} className="btn-secondary">
          {handle?.backTo?.label ?? 'Dashboard'}
        </Link>
      </div>
    </div>
  );
}

export function NotFoundPage() {
  return (
    <div className="card mx-auto mt-16 flex max-w-md flex-col items-center gap-3 p-8 text-center">
      <p className="font-medium">This page doesn&apos;t exist.</p>
      <Link to="/" className="btn-secondary">
        Dashboard
      </Link>
    </div>
  );
}
