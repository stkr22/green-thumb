// Monthly calendar of reminder due dates. Sourced from the dashboard endpoint
// with a horizon wide enough to cover the displayed month; overdue reminders
// surface on today's cell so they're never invisible.

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';

import { useDashboard } from '../api/hooks/useDashboard';
import type { ReminderStatus } from '../api/types';
import { dateKey } from '../lib/dates';

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function monthGrid(year: number, month: number): Date[] {
  const first = new Date(year, month, 1);
  // Monday-based offset of the first day.
  const offset = (first.getDay() + 6) % 7;
  const start = new Date(year, month, 1 - offset);
  return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
}

export function CalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [selectedKey, setSelectedKey] = useState<string>(dateKey(today));

  // Horizon: from now to the end of the displayed month (clamped to >= 1 day).
  const horizonDays = useMemo(() => {
    const endOfMonth = new Date(year, month + 1, 0);
    const days = Math.ceil((endOfMonth.getTime() - Date.now()) / 86_400_000);
    return Math.min(366, Math.max(1, days));
  }, [year, month]);
  const { data } = useDashboard(horizonDays);

  const byDay = useMemo(() => {
    const map = new Map<string, ReminderStatus[]>();
    const push = (key: string, status: ReminderStatus) => {
      map.set(key, [...(map.get(key) ?? []), status]);
    };
    for (const status of data?.upcoming ?? []) {
      if (status.due_at) push(dateKey(new Date(status.due_at)), status);
    }
    for (const status of data?.overdue ?? []) {
      push(dateKey(new Date()), status);
    }
    return map;
  }, [data]);

  const days = monthGrid(year, month);
  const selected = byDay.get(selectedKey) ?? [];
  const monthLabel = new Date(year, month).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  const shiftMonth = (delta: number) => {
    const next = new Date(year, month + delta);
    setYear(next.getFullYear());
    setMonth(next.getMonth());
  };

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Calendar</h1>
        <div className="flex items-center gap-3">
          <button type="button" className="btn-secondary" onClick={() => shiftMonth(-1)} aria-label="Previous month">
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="w-40 text-center font-medium">{monthLabel}</span>
          <button type="button" className="btn-secondary" onClick={() => shiftMonth(1)} aria-label="Next month">
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="card p-4">
        <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-stone-500">
          {WEEKDAYS.map((weekday) => (
            <div key={weekday} className="py-1">
              {weekday}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-1">
          {days.map((day) => {
            const key = dateKey(day);
            const dueCount = byDay.get(key)?.length ?? 0;
            const inMonth = day.getMonth() === month;
            const isToday = key === dateKey(today);
            return (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedKey(key)}
                className={`flex h-16 flex-col items-center rounded-lg border p-1 text-sm ${
                  key === selectedKey ? 'border-emerald-500 bg-emerald-50' : 'border-transparent hover:bg-stone-50'
                } ${inMonth ? 'text-stone-800' : 'text-stone-300'}`}
              >
                <span className={`${isToday ? 'rounded-full bg-emerald-600 px-2 text-white' : ''}`}>
                  {day.getDate()}
                </span>
                {dueCount > 0 && (
                  <span className="mt-1 rounded-full bg-amber-100 px-1.5 text-xs text-amber-700">{dueCount}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <section className="card mt-6 p-5">
        <h2 className="mb-3 font-semibold">Due on {selectedKey}</h2>
        {selected.length === 0 ? (
          <p className="text-sm text-stone-500">Nothing due on this day.</p>
        ) : (
          <ul className="divide-y divide-stone-100">
            {selected.map((status) => (
              <li key={status.reminder_id}>
                <Link
                  to={`/plants/${status.plant_id}`}
                  className="flex items-center justify-between px-2 py-2 hover:bg-stone-50"
                >
                  <span className="font-medium">{status.plant_name}</span>
                  <span className="text-sm capitalize text-stone-500">
                    {status.event_type}
                    {status.overdue && <span className="ml-2 text-red-600">overdue</span>}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
