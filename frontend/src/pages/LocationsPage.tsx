import { useState } from 'react';
import { Check, MapPin, Pencil, Plus, Trash2, X } from 'lucide-react';

import { useCreateLocation, useDeleteLocation, useLocations, useUpdateLocation } from '../api/hooks/useLocations';
import type { LocationRead } from '../api/types';

function LocationRow({ location }: { location: LocationRead }) {
  const updateLocation = useUpdateLocation();
  const deleteLocation = useDeleteLocation();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(location.name);

  return (
    <li className="flex items-center justify-between px-4 py-3">
      {editing ? (
        <form
          className="flex flex-1 items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            updateLocation.mutate({ id: location.id, name }, { onSuccess: () => setEditing(false) });
          }}
        >
          <input className="input-base max-w-xs" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          <button type="submit" title="Save" className="text-emerald-600 hover:text-emerald-800">
            <Check className="h-4 w-4" />
          </button>
          <button type="button" title="Cancel" onClick={() => setEditing(false)} className="text-stone-400">
            <X className="h-4 w-4" />
          </button>
        </form>
      ) : (
        <div className="flex items-center gap-3">
          <MapPin className="h-4 w-4 text-emerald-600" />
          <span className="font-medium">{location.name}</span>
          {location.description && <span className="text-sm text-stone-500">{location.description}</span>}
          <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
            {location.plant_count} {location.plant_count === 1 ? 'plant' : 'plants'}
          </span>
        </div>
      )}
      <div className="flex items-center gap-2">
        <button
          type="button"
          title="Rename"
          className="text-stone-400 hover:text-stone-700"
          onClick={() => setEditing(true)}
        >
          <Pencil className="h-4 w-4" />
        </button>
        <button
          type="button"
          title="Delete"
          className="text-stone-400 hover:text-red-600"
          onClick={() => {
            if (
              window.confirm(
                `Delete ${location.name}? Plants in this location are kept but lose their location.`,
              )
            ) {
              deleteLocation.mutate(location.id);
            }
          }}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </li>
  );
}

export function LocationsPage() {
  const { data: locations = [], isLoading } = useLocations();
  const createLocation = useCreateLocation();
  const [name, setName] = useState('');

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-2xl font-bold">Locations</h1>

      <form
        className="mb-6 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (!name.trim()) return;
          createLocation.mutate({ name: name.trim() }, { onSuccess: () => setName('') });
        }}
      >
        <input
          className="input-base max-w-sm"
          placeholder="New location, e.g. Living room"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <button type="submit" className="btn-primary" disabled={createLocation.isPending}>
          <Plus className="h-4 w-4" />
          Add
        </button>
      </form>

      {isLoading ? (
        <p className="text-stone-500">Loading locations…</p>
      ) : locations.length === 0 ? (
        <p className="text-stone-500">No locations yet. Add rooms or areas where your plants live.</p>
      ) : (
        <ul className="card divide-y divide-stone-100">
          {locations.map((location) => (
            <LocationRow key={location.id} location={location} />
          ))}
        </ul>
      )}
    </div>
  );
}
