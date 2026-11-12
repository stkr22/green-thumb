import { useDeferredValue, useState } from 'react';
import { Link } from 'react-router';
import { Plus, Search } from 'lucide-react';

import { useSuspenseQuery } from '@tanstack/react-query';

import { usePlants } from '../api/hooks/usePlants';
import { locationsQuery } from '../api/queries';
import type { PlantListItem } from '../api/types';
import { PlantCard } from '../components/PlantCard';

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
  // The controls update immediately; the query follows deferred copies. A new
  // filter combination suspends only the deferred render, so React keeps the
  // current grid on screen until the new results arrive (no skeleton flash).
  const deferredSearch = useDeferredValue(search.trim());
  const deferredLocationId = useDeferredValue(locationId);
  const deferredTag = useDeferredValue(tag);
  const filters = {
    search: deferredSearch || undefined,
    locationId: deferredLocationId || undefined,
    tag: deferredTag || undefined,
  };
  const filtered = Boolean(filters.search || filters.locationId || filters.tag);
  const stale = deferredSearch !== search.trim() || deferredLocationId !== locationId || deferredTag !== tag;
  const { data: plants } = usePlants(filters);
  // Tag options come from the unfiltered list (awaited by the route loader),
  // so they don't vanish while a search narrows the results.
  const { data: allPlants } = usePlants();
  const { data: locations } = useSuspenseQuery(locationsQuery);

  const locationNames = new Map(locations.map((location) => [location.id, location.name]));
  // Offer every tag currently in use as a filter option.
  const allTags = [...new Set(allPlants.flatMap((plant) => plant.tags))].sort();
  const sortedPlants = sortPlants(plants, sort);

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
            type="search"
            aria-label="Search plants"
            className="input-base pl-9"
            placeholder="Search by name or species…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <select
          className="input-base w-48"
          aria-label="Filter by location"
          value={locationId}
          onChange={(e) => setLocationId(e.target.value)}
        >
          <option value="">All locations</option>
          {locations.map((location) => (
            <option key={location.id} value={location.id}>
              {location.name}
            </option>
          ))}
        </select>
        <select
          className="input-base w-40"
          aria-label="Filter by tag"
          value={tag}
          onChange={(e) => setTag(e.target.value)}
        >
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

      {plants.length === 0 ? (
        <p className="text-stone-500">
          {filtered ? 'No plants match these filters.' : 'No plants yet. Add your first plant to get started.'}
        </p>
      ) : (
        <div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          aria-busy={stale}
        >
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
