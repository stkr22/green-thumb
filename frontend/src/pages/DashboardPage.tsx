import { Link } from 'react-router-dom';
import { AlertTriangle, CalendarClock, Droplets, Leaf, MapPin } from 'lucide-react';

import { useDashboard } from '../api/hooks/useDashboard';
import type { ReminderStatus } from '../api/types';
import { formatDate, formatDaysAgo } from '../lib/dates';

function ReminderRow({ status, accent }: { status: ReminderStatus; accent: 'red' | 'amber' }) {
  return (
    <Link
      to={`/plants/${status.plant_id}`}
      className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-stone-50"
    >
      <div>
        <span className="font-medium">{status.plant_name}</span>
        <span className="ml-2 text-sm text-stone-500">{status.event_type}</span>
      </div>
      <span className={`text-sm ${accent === 'red' ? 'text-red-600' : 'text-amber-600'}`}>
        {status.due_at ? `due ${formatDate(status.due_at)}` : 'never logged'}
      </span>
    </Link>
  );
}

export function DashboardPage() {
  const { data, isLoading } = useDashboard();

  if (isLoading || !data) {
    return <p className="text-stone-500">Loading dashboard…</p>;
  }

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-6 text-2xl font-bold">Dashboard</h1>

      <div className="mb-6 grid grid-cols-2 gap-4 sm:max-w-md">
        <div className="card flex items-center gap-3 p-4">
          <Leaf className="h-8 w-8 text-emerald-600" />
          <div>
            <p className="text-2xl font-bold">{data.total_plants}</p>
            <p className="text-sm text-stone-500">Plants</p>
          </div>
        </div>
        <div className="card flex items-center gap-3 p-4">
          <MapPin className="h-8 w-8 text-emerald-600" />
          <div>
            <p className="text-2xl font-bold">{data.total_locations}</p>
            <p className="text-sm text-stone-500">Locations</p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card p-5">
          <h2 className="mb-3 flex items-center gap-2 font-semibold">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            Overdue
          </h2>
          {data.overdue.length === 0 ? (
            <p className="text-sm text-stone-500">Nothing overdue. Your plants are happy.</p>
          ) : (
            data.overdue.map((status) => (
              <ReminderRow key={status.reminder_id} status={status} accent="red" />
            ))
          )}
        </section>

        <section className="card p-5">
          <h2 className="mb-3 flex items-center gap-2 font-semibold">
            <CalendarClock className="h-5 w-5 text-amber-500" />
            Next 7 days
          </h2>
          {data.upcoming.length === 0 ? (
            <p className="text-sm text-stone-500">Nothing due this week.</p>
          ) : (
            data.upcoming.map((status) => (
              <ReminderRow key={status.reminder_id} status={status} accent="amber" />
            ))
          )}
        </section>

        <section className="card p-5 lg:col-span-2">
          <h2 className="mb-3 flex items-center gap-2 font-semibold">
            <Droplets className="h-5 w-5 text-sky-500" />
            Recently watered
          </h2>
          {data.recently_watered.length === 0 ? (
            <p className="text-sm text-stone-500">No watering logged yet.</p>
          ) : (
            <ul className="divide-y divide-stone-100">
              {data.recently_watered.map((entry) => (
                <li key={`${entry.plant_id}-${entry.logged_at}`}>
                  <Link
                    to={`/plants/${entry.plant_id}`}
                    className="flex items-center justify-between px-3 py-2 hover:bg-stone-50"
                  >
                    <span className="font-medium">{entry.plant_name}</span>
                    <span className="text-sm text-stone-500">{formatDaysAgo(entry.logged_at)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
