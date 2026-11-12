// Date helpers; the API returns UTC ISO 8601 strings.

const DAY_MS = 24 * 60 * 60 * 1000;

function startOfLocalDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

/**
 * Calendar days between the timestamp and today in local time, so watering at
 * 23:00 reads "yesterday" the next morning instead of "today" (elapsed 24h
 * blocks would say 0). Rounded because DST days are 23 or 25 hours long.
 */
function daysAgo(iso: string, now = new Date()): number {
  return Math.round((startOfLocalDay(now) - startOfLocalDay(new Date(iso))) / DAY_MS);
}

export function formatDaysAgo(iso: string | null | undefined): string {
  if (!iso) return 'never';
  const days = daysAgo(iso);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}

/** Human label for a reminder's next due timestamp (null = no matching event yet). */
export function formatDue(iso: string | null | undefined): string {
  if (!iso) return 'due now (never logged)';
  const msLeft = new Date(iso).getTime() - Date.now();
  const days = Math.ceil(msLeft / DAY_MS);
  if (days < 0) return `${-days} ${days === -1 ? 'day' : 'days'} overdue`;
  if (days === 0) return 'due today';
  if (days === 1) return 'due tomorrow';
  return `due in ${days} days`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Human label for a local-date key from dateKey(), e.g. "12 Nov 2026". */
export function formatDateKey(key: string): string {
  // A date-time without an offset parses as local time (a bare date would be UTC).
  return new Date(`${key}T00:00:00`).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Local-date key (YYYY-MM-DD) used to bucket reminders onto calendar days. */
export function dateKey(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

/**
 * Days from now to the end of the given month (0-based), clamped to the API's
 * 1–366 range: the dashboard horizon that covers that month in the calendar.
 */
export function horizonToEndOfMonth(year: number, month: number, now = Date.now()): number {
  const endOfMonth = new Date(year, month + 1, 0);
  return Math.min(366, Math.max(1, Math.ceil((endOfMonth.getTime() - now) / DAY_MS)));
}
