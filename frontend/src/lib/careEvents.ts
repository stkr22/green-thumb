import { Droplets, FlaskConical, Shovel, Sparkles } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

// Single source of truth for how a care event type looks across the app.
// Event colors only ever render as icon chips with tinted backgrounds; the
// red/amber status colors stay plain text — that contrast is what keeps
// repotting-orange readable next to an amber "due soon" label.
export interface CareEventStyle {
  eventType: string;
  label: string;
  verb: string;
  // Spelled out rather than derived (e.g. `verb + 'ed'`) because the suffix
  // rule breaks on "Fertilise" → "Fertiliseed" and "Repot" → "Repoted".
  pastTense: string;
  Icon: LucideIcon;
  /** Tinted chip: background + text, e.g. for pill badges. */
  chip: string;
  /** Standalone icon color for inline icons without a chip background. */
  icon: string;
}

export const DEFAULT_CARE_EVENTS: CareEventStyle[] = [
  {
    eventType: 'watering',
    label: 'Watering',
    verb: 'Water',
    pastTense: 'Watered',
    Icon: Droplets,
    chip: 'bg-sky-100 text-sky-700',
    icon: 'text-sky-600',
  },
  {
    eventType: 'fertilising',
    label: 'Fertilising',
    verb: 'Fertilise',
    pastTense: 'Fertilised',
    Icon: FlaskConical,
    chip: 'bg-violet-100 text-violet-700',
    icon: 'text-violet-600',
  },
  {
    eventType: 'repotting',
    label: 'Repotting',
    verb: 'Repot',
    pastTense: 'Repotted',
    Icon: Shovel,
    chip: 'bg-orange-100 text-orange-800',
    icon: 'text-orange-600',
  },
];

const BY_TYPE = new Map(DEFAULT_CARE_EVENTS.map((style) => [style.eventType, style]));

/** Style for any event type; custom types get a neutral fallback with the raw name. */
export function careEventStyle(eventType: string): CareEventStyle {
  const known = BY_TYPE.get(eventType);
  if (known) return known;
  const capitalized = eventType.charAt(0).toUpperCase() + eventType.slice(1);
  return {
    eventType,
    label: capitalized,
    verb: capitalized,
    pastTense: capitalized,
    Icon: Sparkles,
    chip: 'bg-stone-100 text-stone-600',
    icon: 'text-stone-500',
  };
}
