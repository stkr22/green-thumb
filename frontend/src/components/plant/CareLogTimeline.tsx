import { useState } from 'react';
import { Trash2 } from 'lucide-react';

import { useCreateLog, useDeleteLog, useLogs } from '../../api/hooks/useLogs';
import { LOGS_PAGE_SIZE } from '../../api/queries';
import { DEFAULT_CARE_EVENTS } from '../../lib/careEvents';
import { formatDateTime } from '../../lib/dates';
import { CareEventChip } from '../CareEventChip';
import { useToast } from '../Toast';

export function CareLogTimeline({ plantId }: { plantId: string }) {
  const [eventType, setEventType] = useState('');
  const [page, setPage] = useState(0);
  const { data: logs = [] } = useLogs(plantId, eventType || undefined, page);
  const deleteLog = useDeleteLog(plantId);
  const createLog = useCreateLog(plantId);
  const { notify } = useToast();

  return (
    <section className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold">Care log</h2>
        <select
          className="input-base w-40"
          aria-label="Filter care log"
          value={eventType}
          onChange={(event) => {
            setEventType(event.target.value);
            setPage(0);
          }}
        >
          <option value="">All events</option>
          {DEFAULT_CARE_EVENTS.map((event) => (
            <option key={event.eventType} value={event.eventType}>
              {event.label}
            </option>
          ))}
        </select>
      </div>
      {logs.length === 0 ? (
        <p className="text-sm text-stone-500">No care events logged{page > 0 ? ' on this page' : ' yet'}.</p>
      ) : (
        <ul className="divide-y divide-stone-100">
          {logs.map((log) => (
            <li key={log.id} className="flex items-center justify-between py-2">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <CareEventChip eventType={log.event_type} />
                  <span className="text-sm text-stone-500">{formatDateTime(log.logged_at)}</span>
                </div>
                {log.notes && <p className="mt-1 text-sm text-stone-500">{log.notes}</p>}
              </div>
              <button
                type="button"
                aria-label={`Delete ${log.event_type} entry`}
                title="Delete log entry"
                className="text-stone-400 hover:text-red-600"
                onClick={() =>
                  deleteLog.mutate(log.id, {
                    onSuccess: () =>
                      // Undo recreates the entry with its original timestamp.
                      notify(`${log.event_type} entry deleted`, 'success', {
                        label: 'Undo',
                        onClick: () =>
                          createLog.mutate({ event_type: log.event_type, notes: log.notes, logged_at: log.logged_at }),
                      }),
                  })
                }
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3 flex gap-2">
        <button type="button" className="btn-secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
          Previous
        </button>
        <button
          type="button"
          className="btn-secondary"
          disabled={logs.length < LOGS_PAGE_SIZE}
          onClick={() => setPage(page + 1)}
        >
          Next
        </button>
      </div>
    </section>
  );
}
