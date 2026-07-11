import { useState } from 'react';
import { Pencil, Plus, Search, Sprout, Trash2 } from 'lucide-react';

import { useCreateSpecies, useDeleteSpecies, useSpecies, useUpdateSpecies } from '../api/hooks/useSpecies';
import type { SpeciesListItem } from '../api/types';
import { Modal } from '../components/Modal';
import { SpeciesForm } from '../components/SpeciesForm';
import { useToast } from '../components/Toast';

function intervalSummary(species: SpeciesListItem): string {
  const entries = Object.entries(species.default_intervals);
  if (entries.length === 0) return '';
  return entries.map(([eventType, days]) => `${eventType} every ${days}d`).join(' · ');
}

function SpeciesRow({ species, onEdit }: { species: SpeciesListItem; onEdit: () => void }) {
  const deleteSpecies = useDeleteSpecies();
  const summary = intervalSummary(species);

  return (
    <li className="flex items-start justify-between gap-3 px-4 py-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Sprout className="h-4 w-4 shrink-0 text-emerald-600" />
          <span className="font-medium">{species.name}</span>
          {species.scientific_name && <span className="text-sm italic text-stone-500">{species.scientific_name}</span>}
          <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
            {species.plant_count} {species.plant_count === 1 ? 'plant' : 'plants'}
          </span>
          {species.toxicity && (
            <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700">{species.toxicity}</span>
          )}
          {species.deadheading && (
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">deadheading</span>
          )}
        </div>
        {summary && <p className="mt-1 text-xs text-stone-500">{summary}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <button type="button" title="Edit" className="text-stone-400 hover:text-stone-700" onClick={onEdit}>
          <Pencil className="h-4 w-4" />
        </button>
        <button
          type="button"
          title="Delete"
          className="text-stone-400 hover:text-red-600"
          onClick={() => {
            if (
              window.confirm(`Delete ${species.name}? Plants of this species are kept but lose the species link.`)
            ) {
              deleteSpecies.mutate(species.id);
            }
          }}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </li>
  );
}

export function SpeciesPage() {
  const [search, setSearch] = useState('');
  const { data: species = [], isLoading } = useSpecies(search || undefined);
  const createSpecies = useCreateSpecies();
  const updateSpecies = useUpdateSpecies();
  const { notify } = useToast();
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<SpeciesListItem | null>(null);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Species</h1>
        <button type="button" className="btn-primary" onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4" />
          Add species
        </button>
      </div>

      <div className="relative mb-6 max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
        <input
          className="input-base pl-9"
          placeholder="Search species…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      {isLoading ? (
        <p className="text-stone-500">Loading species…</p>
      ) : species.length === 0 ? (
        <p className="text-stone-500">
          {search
            ? 'No species match your search.'
            : 'No species yet. Add one to share care advice and default reminders across plants of the same kind.'}
        </p>
      ) : (
        <ul className="card divide-y divide-stone-100">
          {species.map((item) => (
            <SpeciesRow key={item.id} species={item} onEdit={() => setEditing(item)} />
          ))}
        </ul>
      )}

      <Modal title="Add species" open={addOpen} onClose={() => setAddOpen(false)}>
        <SpeciesForm
          submitLabel="Create species"
          busy={createSpecies.isPending}
          onSubmit={(payload) => {
            createSpecies.mutate(payload, {
              onSuccess: (created) => {
                notify(`${created.name} created`);
                setAddOpen(false);
              },
            });
          }}
        />
      </Modal>

      <Modal title={`Edit ${editing?.name ?? ''}`} open={editing !== null} onClose={() => setEditing(null)}>
        {editing && (
          <SpeciesForm
            initial={editing}
            submitLabel="Save changes"
            busy={updateSpecies.isPending}
            onSubmit={(payload) => {
              updateSpecies.mutate(
                { id: editing.id, ...payload },
                {
                  onSuccess: () => {
                    notify(`${payload.name} updated`);
                    setEditing(null);
                  },
                },
              );
            }}
          />
        )}
      </Modal>
    </div>
  );
}
