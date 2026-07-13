import type { ReactNode } from 'react';

import { careEventStyle } from '../lib/careEvents';

interface CareEventChipProps {
  eventType: string;
  /** Overrides the chip text; defaults to the event label (e.g. "Watering"). */
  children?: ReactNode;
}

// The one way care event types are color coded across the app: a tinted pill
// with the event icon, so rows stay scannable on small screens.
export function CareEventChip({ eventType, children }: CareEventChipProps) {
  const event = careEventStyle(eventType);
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${event.chip}`}
    >
      <event.Icon className="h-3 w-3" />
      {children ?? event.label}
    </span>
  );
}
