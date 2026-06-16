import { Link } from 'react-router-dom';
import { Droplets, Leaf, MapPin } from 'lucide-react';

import { thumbnailUrl } from '../api/client';
import type { PlantListItem } from '../api/types';
import { formatDaysAgo } from '../lib/dates';

interface PlantCardProps {
  plant: PlantListItem;
  locationName?: string;
}

export function PlantCard({ plant, locationName }: PlantCardProps) {
  return (
    <Link to={`/plants/${plant.id}`} className="card overflow-hidden transition hover:shadow-md">
      {plant.cover_photo_id ? (
        <img src={thumbnailUrl(plant.cover_photo_id)} alt={plant.name} className="h-40 w-full object-cover" />
      ) : (
        <div className="flex h-40 w-full items-center justify-center bg-emerald-50">
          <Leaf className="h-10 w-10 text-emerald-300" />
        </div>
      )}
      <div className="p-4">
        <h3 className="font-semibold">{plant.name}</h3>
        {plant.species_name && <p className="text-sm italic text-stone-500">{plant.species_name}</p>}
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
        {plant.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {plant.tags.map((tag) => (
              <span key={tag} className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}
