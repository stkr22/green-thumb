import { useState } from 'react';
import { AlarmClock, AlarmClockOff, Plus, Trash2 } from 'lucide-react';

import {
  useCreateReminder,
  useDeleteReminder,
  useReminders,
  useSnoozeReminder,
  useUnsnoozeReminder,
  useUpdateReminder,
} from '../../api/hooks/useReminders';
import type { ReminderStatusRead } from '../../api/types';
import { DEFAULT_CARE_EVENTS } from '../../lib/careEvents';
import { formatDate, formatDue } from '../../lib/dates';
import { isSnoozed, snoozeDays } from '../../lib/reminders';
import { type MonthWindow, paceLabel, windowLabel } from '../../lib/seasons';
import { CareEventChip } from '../CareEventChip';
import { Field } from '../Field';
import { MonthWindowPicker } from '../MonthWindowPicker';
import { useToast } from '../Toast';

// Matching the quick-action event types exactly is what links a reminder to
// its care logs, so the picker offers them instead of free text (typo-proof);
// "custom" still allows arbitrary event types.
const CUSTOM_EVENT = '__custom__';

/** How often this reminder currently fires, labelled with the season when it differs. */
function ReminderPace({ reminder }: { reminder: ReminderStatusRead }) {
  if (reminder.window_start_month && reminder.window_end_month) {
    return (
      <span className="text-sm text-stone-500">
        every {reminder.interval_days} days
        <span className="text-stone-400">
          {' '}
          · in {windowLabel(reminder.window_start_month, reminder.window_end_month)}
        </span>
      </span>
    );
  }
  if (reminder.paused) {
    return <span className="text-sm text-stone-500">every {reminder.interval_days} days in season</span>;
  }
  const days = snoozeDays(reminder);
  return (
    <span className="text-sm text-stone-500">
      every {days} days
      {days !== reminder.interval_days && <span className="text-stone-400"> · {paceLabel(reminder.season)}</span>}
    </span>
  );
}

function ReminderDueLabel({ reminder }: { reminder: ReminderStatusRead }) {
  // "off" rather than "paused": seasonal pausing is a separate, automatic state.
  if (!reminder.enabled) return <span className="text-sm text-stone-400">off</span>;
  const dueAt = reminder.due_at ?? null;
  if (reminder.paused) {
    return (
      <span className="text-sm text-stone-400">
        paused for {reminder.season}
        {dueAt && ` · resumes ${formatDate(dueAt)}`}
      </span>
    );
  }
  if (isSnoozed(reminder) && reminder.snoozed_until) {
    return <span className="text-sm text-stone-400">snoozed until {formatDate(reminder.snoozed_until)}</span>;
  }
  const overdue = !dueAt || new Date(dueAt).getTime() <= Date.now();
  return <span className={`text-sm ${overdue ? 'font-medium text-red-600' : 'text-stone-500'}`}>{formatDue(dueAt)}</span>;
}

function ReminderRow({ reminder, plantId }: { reminder: ReminderStatusRead; plantId: string }) {
  const createReminder = useCreateReminder(plantId);
  const updateReminder = useUpdateReminder(plantId);
  const deleteReminder = useDeleteReminder(plantId);
  const snoozeReminder = useSnoozeReminder();
  const unsnoozeReminder = useUnsnoozeReminder();
  const { notify } = useToast();
  const ids = { reminderId: reminder.id, plantId };

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <CareEventChip eventType={reminder.event_type} />
        <ReminderPace reminder={reminder} />
        <ReminderDueLabel reminder={reminder} />
      </div>
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1 text-sm text-stone-500">
          <input
            type="checkbox"
            checked={reminder.enabled}
            onChange={(event) => updateReminder.mutate({ id: reminder.id, enabled: event.target.checked })}
          />
          enabled
        </label>
        {isSnoozed(reminder) ? (
          <button
            type="button"
            title="Cancel snooze"
            aria-label={`Cancel ${reminder.event_type} snooze`}
            className="text-stone-400 hover:text-emerald-600"
            disabled={unsnoozeReminder.isPending}
            onClick={() => unsnoozeReminder.mutate(ids)}
          >
            <AlarmClockOff className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="button"
            title={`Snooze for ${snoozeDays(reminder)} days`}
            className="text-stone-400 hover:text-emerald-600"
            disabled={snoozeReminder.isPending}
            onClick={() =>
              snoozeReminder.mutate(ids, {
                onSuccess: () =>
                  notify(`${reminder.event_type} snoozed for ${snoozeDays(reminder)} days`, 'success', {
                    label: 'Undo',
                    onClick: () => unsnoozeReminder.mutate(ids),
                  }),
              })
            }
          >
            <AlarmClock className="h-4 w-4" />
          </button>
        )}
        <button
          type="button"
          title="Delete reminder"
          aria-label={`Delete ${reminder.event_type} reminder`}
          className="text-stone-400 hover:text-red-600"
          onClick={() =>
            deleteReminder.mutate(reminder.id, {
              onSuccess: () =>
                notify(`${reminder.event_type} reminder deleted`, 'success', {
                  label: 'Undo',
                  onClick: () =>
                    createReminder.mutate({
                      event_type: reminder.event_type,
                      interval_days: reminder.interval_days,
                      enabled: reminder.enabled,
                      // Undo has to restore the schedule too, or the
                      // reminder comes back on a different cadence.
                      season_multipliers: reminder.season_multipliers,
                      schedule_kind: reminder.schedule_kind === 'annual_window' ? 'annual_window' : 'interval',
                      window_start_month: reminder.window_start_month,
                      window_end_month: reminder.window_end_month,
                    }),
                }),
            })
          }
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </li>
  );
}

function AddReminderForm({ plantId }: { plantId: string }) {
  const createReminder = useCreateReminder(plantId);
  const [eventChoice, setEventChoice] = useState('watering');
  const [customEvent, setCustomEvent] = useState('');
  const [intervalDays, setIntervalDays] = useState(7);
  // null means a plain interval; a month pair makes it an annual-window
  // reminder, whose due date waits for those months.
  const [monthWindow, setMonthWindow] = useState<MonthWindow | null>(null);

  return (
    <form
      className="flex flex-wrap items-end gap-2"
      aria-label="Add reminder"
      onSubmit={(event) => {
        event.preventDefault();
        const eventType = eventChoice === CUSTOM_EVENT ? customEvent.trim() : eventChoice;
        if (!eventType) return;
        createReminder.mutate(
          {
            event_type: eventType,
            interval_days: intervalDays,
            enabled: true,
            schedule_kind: monthWindow ? 'annual_window' : 'interval',
            window_start_month: monthWindow?.[0],
            window_end_month: monthWindow?.[1],
          },
          { onSuccess: () => setCustomEvent('') },
        );
      }}
    >
      <Field label="Event" size="sm">
        {(id) => (
          <select id={id} className="input-base w-36" value={eventChoice} onChange={(e) => setEventChoice(e.target.value)}>
            {DEFAULT_CARE_EVENTS.map(({ eventType, label }) => (
              <option key={eventType} value={eventType}>
                {label}
              </option>
            ))}
            <option value={CUSTOM_EVENT}>Custom…</option>
          </select>
        )}
      </Field>
      {eventChoice === CUSTOM_EVENT && (
        <Field label="Custom event" size="sm">
          {(id) => (
            <input
              id={id}
              className="input-base w-36"
              placeholder="misting"
              value={customEvent}
              onChange={(e) => setCustomEvent(e.target.value)}
            />
          )}
        </Field>
      )}
      <Field label="Every (days)" size="sm">
        {(id) => (
          <input
            id={id}
            type="number"
            min={1}
            max={3650}
            required
            className="input-base w-28"
            value={intervalDays}
            onChange={(e) => setIntervalDays(Number(e.target.value))}
          />
        )}
      </Field>
      <MonthWindowPicker
        value={monthWindow}
        onChange={setMonthWindow}
        name="Window"
        startLabel="Only in"
        endLabel="through"
        anyLabel="Any month"
      />
      <button type="submit" className="btn-primary" disabled={createReminder.isPending}>
        <Plus className="h-4 w-4" />
        Add reminder
      </button>
    </form>
  );
}

export function RemindersSection({ plantId }: { plantId: string }) {
  const { data: reminders = [] } = useReminders(plantId);

  return (
    <section className="card p-5" aria-labelledby="reminders-heading">
      <h2 id="reminders-heading" className="mb-3 font-semibold">
        Reminders
      </h2>
      {reminders.length === 0 ? (
        <p className="mb-3 text-sm text-stone-500">No reminders configured.</p>
      ) : (
        <ul className="mb-4 divide-y divide-stone-100" aria-label="Reminders">
          {reminders.map((reminder) => (
            <ReminderRow key={reminder.id} reminder={reminder} plantId={plantId} />
          ))}
        </ul>
      )}
      <AddReminderForm plantId={plantId} />
    </section>
  );
}
