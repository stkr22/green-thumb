// One tappable card per default care type. The "last done" display and the
// log buttons used to be separate elements, which invited taps on the read-only
// half; merging them makes the whole card the action, with an Undo toast as
// the safety net for accidental taps.

import { Plus } from 'lucide-react';

import { useCreateLog, useDeleteLog } from '../../api/hooks/useLogs';
import { useReminders } from '../../api/hooks/useReminders';
import type { PlantDetail, ReminderStatusRead } from '../../api/types';
import { DEFAULT_CARE_EVENTS } from '../../lib/careEvents';
import { formatDaysAgo, formatDue } from '../../lib/dates';
import { isSnoozed } from '../../lib/reminders';
import { useToast } from '../Toast';

const DUE_SOON_MS = 2 * 24 * 60 * 60 * 1000;

function DueHint({ reminder }: { reminder: ReminderStatusRead | undefined }) {
  if (!reminder) return null;
  if (isSnoozed(reminder)) return <span className="text-xs text-stone-400">snoozed</span>;
  const msLeft = reminder.due_at ? new Date(reminder.due_at).getTime() - Date.now() : null;
  if (msLeft === null || msLeft <= 0) {
    return <span className="text-xs font-medium text-red-600">{formatDue(reminder.due_at ?? null)}</span>;
  }
  if (msLeft <= DUE_SOON_MS) return <span className="text-xs font-medium text-amber-600">{formatDue(reminder.due_at)}</span>;
  return null;
}

export function CareActions({ plant, onCustom }: { plant: PlantDetail; onCustom: () => void }) {
  const createLog = useCreateLog(plant.id);
  const deleteLog = useDeleteLog(plant.id);
  const { data: reminders = [] } = useReminders(plant.id);
  const { notify } = useToast();

  return (
    <div>
      <div className="grid grid-cols-3 gap-2">
        {DEFAULT_CARE_EVENTS.map((event) => (
          <button
            key={event.eventType}
            type="button"
            className="card flex flex-col items-start gap-1 p-3 text-left transition hover:shadow-md disabled:opacity-50"
            disabled={createLog.isPending}
            onClick={() =>
              createLog.mutate(
                { event_type: event.eventType },
                {
                  onSuccess: (log) =>
                    notify(event.pastTense, 'success', { label: 'Undo', onClick: () => deleteLog.mutate(log.id) }),
                },
              )
            }
          >
            <span className={`rounded-full p-1.5 ${event.chip}`}>
              <event.Icon className="h-4 w-4" />
            </span>
            <span className="text-sm font-medium">{event.verb}</span>
            <span className="text-xs text-stone-500">
              {event.pastTense} {formatDaysAgo(plant.last_events?.[event.eventType])}
            </span>
            <DueHint reminder={reminders.find((r) => r.event_type === event.eventType && r.enabled)} />
          </button>
        ))}
      </div>
      <div className="mt-2">
        <button type="button" className="btn-secondary" onClick={onCustom}>
          <Plus className="h-4 w-4" />
          Custom
        </button>
      </div>
    </div>
  );
}
