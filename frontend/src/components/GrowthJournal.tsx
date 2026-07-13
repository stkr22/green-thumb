// Growth journal: photos and care events merged into one chronological story,
// grouped by month. The data already exists (photo timestamps + care logs);
// this is purely a different lens on it.

import { useQuery } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';

import { api, photoUrl, thumbnailUrl } from '../api/client';
import { usePhotos } from '../api/hooks/usePhotos';
import type { CareLogRead, PhotoRead } from '../api/types';
import { careEventStyle } from '../lib/careEvents';
import { formatDate } from '../lib/dates';

const JOURNAL_LOG_LIMIT = 500;

// Shares the ['plants', id, 'logs'] prefix, so care-log mutations refresh it.
function useJournalLogs(plantId: string) {
  return useQuery({
    queryKey: ['plants', plantId, 'logs', 'journal'],
    queryFn: () => api<CareLogRead[]>(`/api/v1/plants/${plantId}/logs?limit=${JOURNAL_LOG_LIMIT}`),
  });
}

type Entry =
  | { at: string; kind: 'photo'; photo: PhotoRead }
  | { at: string; kind: 'event'; log: CareLogRead };

function monthLabel(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
}

export function GrowthJournal({ plantId }: { plantId: string }) {
  const { data: logs = [] } = useJournalLogs(plantId);
  const { data: photos = [] } = usePhotos(plantId);

  const entries: Entry[] = [
    ...photos.map((photo): Entry => ({ at: photo.uploaded_at, kind: 'photo', photo })),
    ...logs.map((log): Entry => ({ at: log.logged_at, kind: 'event', log })),
  ].sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime());

  if (entries.length === 0) return null;

  const byMonth = new Map<string, Entry[]>();
  for (const entry of entries) {
    const label = monthLabel(entry.at);
    byMonth.set(label, [...(byMonth.get(label) ?? []), entry]);
  }

  return (
    <section className="card p-5">
      <h2 className="mb-4 flex items-center gap-2 font-semibold">
        <BookOpen className="h-4 w-4 text-emerald-600" />
        Growth journal
      </h2>
      <div className="flex flex-col gap-5">
        {[...byMonth.entries()].map(([month, monthEntries]) => (
          <div key={month}>
            <h3 className="mb-2 text-sm font-medium text-stone-500">{month}</h3>
            <ol className="flex flex-col gap-3 border-l-2 border-emerald-100 pl-4">
              {monthEntries.map((entry) =>
                entry.kind === 'photo' ? (
                  <li key={`photo-${entry.photo.id}`} className="flex items-center gap-3">
                    <a href={photoUrl(entry.photo.id)} target="_blank" rel="noreferrer" className="shrink-0">
                      <img
                        src={thumbnailUrl(entry.photo.id)}
                        alt={`Photo from ${formatDate(entry.at)}`}
                        className="h-20 w-20 rounded-lg object-cover transition hover:opacity-90"
                      />
                    </a>
                    <span className="text-sm text-stone-500">Photo · {formatDate(entry.at)}</span>
                  </li>
                ) : (
                  <li key={`log-${entry.log.id}`} className="flex items-start gap-2">
                    {(() => {
                      const event = careEventStyle(entry.log.event_type);
                      return <event.Icon className={`mt-0.5 h-4 w-4 shrink-0 ${event.icon}`} />;
                    })()}
                    <div className="text-sm">
                      <span className="font-medium capitalize">{entry.log.event_type}</span>
                      <span className="ml-2 text-stone-500">{formatDate(entry.at)}</span>
                      {entry.log.notes && <p className="text-stone-600">{entry.log.notes}</p>}
                    </div>
                  </li>
                ),
              )}
            </ol>
          </div>
        ))}
      </div>
      {logs.length === JOURNAL_LOG_LIMIT && (
        <p className="mt-3 text-xs text-stone-400">Showing the latest {JOURNAL_LOG_LIMIT} events.</p>
      )}
    </section>
  );
}
