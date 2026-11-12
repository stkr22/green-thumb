// Reminder display rules shared by the dashboard and the plant detail page.

interface Snoozable {
  snoozed_until?: string | null;
}

interface Paced {
  interval_days: number;
  effective_interval_days?: number | null;
}

export function isSnoozed(reminder: Snoozable | undefined, now = Date.now()): boolean {
  return Boolean(reminder?.snoozed_until && new Date(reminder.snoozed_until).getTime() > now);
}

/** Snoozing defers by the current season's pace, so labels have to say that number. */
export function snoozeDays(reminder: Paced): number {
  return reminder.effective_interval_days ?? reminder.interval_days;
}
