// Season plan helpers shared by the species form, the plant detail reminders
// and the dashboard banner.
//
// The API speaks multipliers on the growing-season interval, but people think
// in days ("every 14 days in winter"), so the editor converts in both
// directions and only multipliers ever cross the wire.

export const SEASONS = [
  { key: 'spring', label: 'Spring' },
  { key: 'summer', label: 'Summer' },
  { key: 'autumn', label: 'Autumn' },
  { key: 'winter', label: 'Winter' },
] as const;

export type SeasonKey = (typeof SEASONS)[number]['key'];

/** season -> multiplier on the base interval; null pauses that season. */
export type SeasonMultipliers = Record<string, number | null>;
export type SeasonPlan = Record<string, SeasonMultipliers>;

// Seasonal pacing only applies where "skip the dormant days" is the right
// meaning. Repotting and other one-off jobs need a fixed spring window
// instead, so the editor leaves them out rather than pretending.
export const SEASONAL_EVENT_TYPES = ['watering', 'fertilising'] as const;

// Care that belongs in a fixed part of the year rather than merely slowing
// down: the interval keeps running and only the due date waits for the window.
export const WINDOWED_EVENT_TYPES = ['repotting'] as const;

export const MONTHS = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
] as const;

export type MonthWindow = [number, number];

export function monthLabel(month: number): string {
  return MONTHS[month - 1] ?? String(month);
}

/** "Mar–May", or "Nov–Feb" for a window that wraps the year. */
export function windowLabel(start: number, end: number): string {
  return `${monthLabel(start)}–${monthLabel(end)}`;
}

export function seasonLabel(season: string): string {
  return SEASONS.find((entry) => entry.key === season)?.label ?? season;
}

/** "winter pace" — appended to an interval so a changed schedule explains itself. */
export function paceLabel(season: string): string {
  return `${season} pace`;
}

/** Interval in days at one season's pace; null when that season is paused. */
export function seasonDays(baseDays: number, multiplier: number | null | undefined): number | null {
  if (multiplier === null) return null;
  return Math.max(1, Math.round(baseDays * (multiplier ?? 1)));
}

/** The multiplier that expresses "this many days" against the base interval. */
export function daysToMultiplier(baseDays: number, days: number): number {
  if (baseDays <= 0) return 1;
  return Math.round((days / baseDays) * 1000) / 1000;
}

/** True when a plan leaves every season at the base interval, i.e. is not worth storing. */
export function isNeutral(multipliers: SeasonMultipliers | undefined): boolean {
  if (!multipliers) return true;
  return SEASONS.every(({ key }) => {
    const value = multipliers[key];
    return value === undefined || value === 1;
  });
}
