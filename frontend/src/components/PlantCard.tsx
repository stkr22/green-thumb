import { Link } from 'react-router';
import { Droplets, Leaf, MapPin } from 'lucide-react';

import { thumbnailUrl } from '../api/client';
import { useCreateLog } from '../api/hooks/useLogs';
import type { PlantListItem } from '../api/types';
import { CareEventChip } from './CareEventChip';
import { useToast } from './Toast';
import { careEventStyle } from '../lib/careEvents';
import { formatDaysAgo } from '../lib/dates';

interface PlantCardProps {
  plant: PlantListItem;
  locationName?: string;
}

export function PlantCard({ plant, locationName }: PlantCardProps) {
  const createLog = useCreateLog(plant.id);
  const { notify } = useToast();

  // The title link is "stretched" over the whole card (its ::after covers it),
  // while the quick-log buttons sit above it as siblings. Buttons nested inside
  // a link are invalid HTML and made the whole card read as one link.
  return (
    <article className="card relative overflow-hidden transition hover:shadow-md">
      {plant.cover_photo_id ? (
        <img
          src={thumbnailUrl(plant.cover_photo_id)}
          alt=""
          loading="lazy"
          width={400}
          height={160}
          className="h-40 w-full object-cover"
        />
      ) : (
        <div className="flex h-40 w-full items-center justify-center bg-emerald-50">
          <Leaf className="h-10 w-10 text-emerald-300" />
        </div>
      )}
      <div className="p-4">
        <h3 className="font-semibold">
          <Link to={`/plants/${plant.id}`} className="after:absolute after:inset-0 after:content-['']">
            {plant.name}
          </Link>
        </h3>
        {plant.species_display_name && (
          <p className="text-sm italic text-stone-500">{plant.species_display_name}</p>
        )}
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-stone-500">
          {locationName && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {locationName}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Droplets className="h-3 w-3 text-sky-500" />
            {plant.last_watered_at ? `watered ${formatDaysAgo(plant.last_watered_at)}` : 'never watered'}
          </span>
        </div>
        {(plant.due_events ?? []).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {(plant.due_events ?? []).map((eventType) => (
              <CareEventChip key={eventType} eventType={eventType}>
                {careEventStyle(eventType).verb} due
              </CareEventChip>
            ))}
          </div>
        )}
        {plant.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {plant.tags.map((tag) => (
              <span key={tag} className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
                {tag}
              </span>
            ))}
          </div>
        )}
        <div className="relative z-10 mt-3 flex gap-2">
          {['watering', 'fertilising'].map((eventType) => {
            const event = careEventStyle(eventType);
            return (
              <button
                key={eventType}
                type="button"
                className="btn-secondary flex-1"
                aria-label={`${event.verb} ${plant.name}`}
                disabled={createLog.isPending}
                onClick={() =>
                  createLog.mutate({ event_type: eventType }, { onSuccess: () => notify(`${event.verb} logged`) })
                }
              >
                <event.Icon className={`h-4 w-4 ${event.icon}`} />
                {event.verb}
              </button>
            );
          })}
        </div>
      </div>
    </article>
  );
}
