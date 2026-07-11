// Pulsing placeholders shown while queries load, sized like the real content
// so the layout doesn't jump when data arrives.

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-stone-200 ${className}`} />;
}

export function PlantCardSkeleton() {
  return (
    <div className="card overflow-hidden">
      <Skeleton className="h-40 w-full rounded-none" />
      <div className="flex flex-col gap-2 p-4">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-8 w-full" />
      </div>
    </div>
  );
}

export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card flex flex-col gap-3 p-5">
      <Skeleton className="h-5 w-1/3" />
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton key={index} className="h-4 w-full" />
      ))}
    </div>
  );
}
