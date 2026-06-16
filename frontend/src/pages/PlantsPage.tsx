import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';

import { useLocations } from '../api/hooks/useLocations';
import { usePlants } from '../api/hooks/usePlants';
import { PlantCard } from '../components/PlantCard';

export function PlantsPage() {
  const [search, setSearch] = useState('');
  const [locationId, setLocationId] = useState('');
  const [tag, setTag] = useState('');
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
      </div>

      {isLoading ? (
        <p className="text-stone-500">Loading plants…</p>
      ) : plants.length === 0 ? (
        <p className="text-stone-500">No plants found. Add your first plant to get started.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {plants.map((plant) => (
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
