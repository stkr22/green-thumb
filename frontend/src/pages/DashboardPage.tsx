import { Link } from 'react-router-dom';
import { AlarmClock, AlertTriangle, CalendarClock, Check, Droplets, Leaf, MapPin } from 'lucide-react';

import { useDashboard } from '../api/hooks/useDashboard';
import { useCreateLogForPlant } from '../api/hooks/useLogs';
import { useSnoozeReminder, useUnsnoozeReminder } from '../api/hooks/useReminders';
import type { ReminderStatus } from '../api/types';
import { CareEventChip } from '../components/CareEventChip';
import { CardSkeleton } from '../components/Skeleton';
import { useToast } from '../components/Toast';
import { formatDate, formatDaysAgo } from '../lib/dates';

function ReminderRow({ status, accent }: { status: ReminderStatus; accent: 'red' | 'amber' }) {
  const createLog = useCreateLogForPlant();
  const snoozeReminder = useSnoozeReminder();
  const unsnoozeReminder = useUnsnoozeReminder();
  const { notify } = useToast();
  const snoozed = Boolean(status.snoozed_until && new Date(status.snoozed_until).getTime() > Date.now());

  return (
    <Link
      to={`/plants/${status.plant_id}`}
      className="flex items-center justify-between gap-2 rounded-lg px-3 py-2 hover:bg-stone-50"
    >
      <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-medium">{status.plant_name}</span>
        <CareEventChip eventType={status.event_type} />
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className={`text-sm ${snoozed ? 'text-stone-400' : accent === 'red' ? 'text-red-600' : 'text-amber-600'}`}>
          {snoozed ? 'snoozed' : status.due_at ? `due ${formatDate(status.due_at)}` : 'never logged'}
        </span>
        {!snoozed && (
          <button
            type="button"
            title={`Snooze ${status.event_type} for ${status.interval_days} days`}
            className="btn-secondary px-2 py-1"
            disabled={snoozeReminder.isPending}
            onClick={(event) => {
              // Rendered inside the row's <Link>: don't navigate, just snooze.
              event.preventDefault();
              event.stopPropagation();
              snoozeReminder.mutate(
                { reminderId: status.reminder_id, plantId: status.plant_id },
                {
                  onSuccess: () =>
                    notify(`${status.event_type} snoozed for ${status.interval_days} days`, 'success', {
                      label: 'Undo',
                      onClick: () =>
                        unsnoozeReminder.mutate({ reminderId: status.reminder_id, plantId: status.plant_id }),
                    }),
                },
              );
            }}
          >
            <AlarmClock className="h-4 w-4" />
          </button>
        )}
        <button
          type="button"
          title={`Log ${status.event_type} for ${status.plant_name}`}
          className="btn-secondary px-2 py-1"
          disabled={createLog.isPending}
          onClick={(event) => {
            // Rendered inside the row's <Link>: don't navigate, just log.
            event.preventDefault();
            event.stopPropagation();
            createLog.mutate(
              { plantId: status.plant_id, event_type: status.event_type },
              { onSuccess: () => notify(`${status.event_type} logged for ${status.plant_name}`) },
            );
          }}
        >
          <Check className="h-4 w-4" />
          Done
        </button>
      </div>
    </Link>
  );
}

function WaterAllButton({ overdue }: { overdue: ReminderStatus[] }) {
  const createLog = useCreateLogForPlant();
  const { notify } = useToast();
  // One plant can have several overdue reminders; watering is per plant.
  const plants = [...new Map(overdue.filter((s) => s.event_type === 'watering').map((s) => [s.plant_id, s])).values()];
  if (plants.length < 2) return null;

  return (
    <button
      type="button"
      className="btn-secondary"
      disabled={createLog.isPending}
      onClick={async () => {
        for (const status of plants) {
          await createLog.mutateAsync({ plantId: status.plant_id, event_type: 'watering' });
        }
        notify(`Watering logged for ${plants.length} plants`);
      }}
    >
      <Droplets className="h-4 w-4 text-sky-500" />
      Water all ({plants.length})
    </button>
  );
}

export function DashboardPage() {
  const { data, isLoading } = useDashboard();

  if (isLoading || !data) {
    return (
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-6 text-2xl font-bold">Dashboard</h1>
        <div className="grid gap-6 lg:grid-cols-2">
          <CardSkeleton lines={3} />
          <CardSkeleton lines={3} />
          <div className="lg:col-span-2">
            <CardSkeleton lines={4} />
          </div>
        </div>
      </div>
    );
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
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Overdue
            </h2>
            <WaterAllButton overdue={data.overdue} />
          </div>
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
