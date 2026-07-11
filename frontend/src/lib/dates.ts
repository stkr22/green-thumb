// Date helpers; the API returns UTC ISO 8601 strings.

export function daysAgo(iso: string): number {
  const elapsed = Date.now() - new Date(iso).getTime();
  return Math.floor(elapsed / (24 * 60 * 60 * 1000));
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
  const days = Math.ceil(msLeft / (24 * 60 * 60 * 1000));
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

/** Local-date key (YYYY-MM-DD) used to bucket reminders onto calendar days. */
export function dateKey(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}
