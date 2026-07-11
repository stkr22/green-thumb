import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';

import { useLocations } from '../api/hooks/useLocations';
import { usePlants } from '../api/hooks/usePlants';
import type { PlantListItem } from '../api/types';
import { PlantCard } from '../components/PlantCard';
import { PlantCardSkeleton } from '../components/Skeleton';

type SortKey = 'name' | 'thirstiest' | 'recently_watered';

// The API returns name order; the other sorts are client-side because the
// whole collection is already loaded (homelab-sized).
function sortPlants(plants: PlantListItem[], sort: SortKey): PlantListItem[] {
  if (sort === 'name') return plants;
  const time = (plant: PlantListItem) =>
    plant.last_watered_at ? new Date(plant.last_watered_at).getTime() : 0; // never watered = thirstiest
  return [...plants].sort((a, b) => (sort === 'thirstiest' ? time(a) - time(b) : time(b) - time(a)));
}

export function PlantsPage() {
  const [search, setSearch] = useState('');
  const [locationId, setLocationId] = useState('');
  const [tag, setTag] = useState('');
  const [sort, setSort] = useState<SortKey>('name');
  const { data: plants = [], isLoading } = usePlants({
    search: search || undefined,
    locationId: locationId || undefined,
    tag: tag || undefined,
  });
  const { data: locations = [] } = useLocations();

  const locationNames = useMemo(
    () => new Map(locations.map((location) => [location.id, location.name])),
    [locations],
  );
  // Offer every tag currently in use as a filter option.
  const allTags = useMemo(() => [...new Set(plants.flatMap((plant) => plant.tags))].sort(), [plants]);
  const sortedPlants = useMemo(() => sortPlants(plants, sort), [plants, sort]);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Plants</h1>
        <Link to="/plants/new" className="btn-primary">
          <Plus className="h-4 w-4" />
          Add plant
        </Link>
      </div>

      <div className="mb-6 flex flex-wrap gap-3">
        <div className="relative min-w-64 flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-stone-400" />
          <input
            className="input-base pl-9"
            placeholder="Search by name or species…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <select className="input-base w-48" value={locationId} onChange={(e) => setLocationId(e.target.value)}>
          <option value="">All locations</option>
          {locations.map((location) => (
            <option key={location.id} value={location.id}>
              {location.name}
            </option>
          ))}
        </select>
        <select className="input-base w-40" value={tag} onChange={(e) => setTag(e.target.value)}>
          <option value="">All tags</option>
          {allTags.map((tagOption) => (
            <option key={tagOption} value={tagOption}>
              {tagOption}
            </option>
          ))}
        </select>
        <select
          className="input-base w-48"
          value={sort}
          onChange={(e) => setSort(e.target.value as SortKey)}
          aria-label="Sort plants"
        >
          <option value="name">Sort by name</option>
          <option value="thirstiest">Longest unwatered first</option>
          <option value="recently_watered">Recently watered first</option>
        </select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }, (_, index) => (
            <PlantCardSkeleton key={index} />
          ))}
        </div>
      ) : plants.length === 0 ? (
        <p className="text-stone-500">No plants found. Add your first plant to get started.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {sortedPlants.map((plant) => (
            <PlantCard
              key={plant.id}
              plant={plant}
              locationName={plant.location_id ? locationNames.get(plant.location_id) : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
