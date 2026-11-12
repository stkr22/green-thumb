// Pulsing placeholder for a page whose data isn't there yet. Pages render with
// their data already loaded (route loaders await it), so this only appears on
// the very first load and while a Suspense boundary waits.

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-stone-200 ${className}`} />;
}

export function PageSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading" className="mx-auto flex max-w-5xl flex-col gap-6 p-4 md:p-8">
      <Skeleton className="h-8 w-48" />
      <div className="card flex flex-col gap-3 p-5">
        <Skeleton className="h-5 w-1/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
}
