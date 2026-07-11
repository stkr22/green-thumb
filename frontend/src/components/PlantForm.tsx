// Shared create/edit plant form (React Hook Form + Zod). Tags are entered as a
// comma-separated string and converted on submit. Species is picked from the
// shared species library (with inline creation); the free-text species fields
// only appear for plants without a species link.

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus } from 'lucide-react';
import { z } from 'zod';

import { useLocations } from '../api/hooks/useLocations';
import { useCreateSpecies, useSpecies } from '../api/hooks/useSpecies';
import type { PlantCreate, PlantDetail } from '../api/types';
import { Modal } from './Modal';
import { SpeciesForm } from './SpeciesForm';

const plantFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  species_id: z.string(),
  species_name: z.string(),
  scientific_name: z.string(),
  location_id: z.string(),
  notes: z.string(),
  tags: z.string(),
});

type PlantFormValues = z.infer<typeof plantFormSchema>;

export function toPlantPayload(values: PlantFormValues): PlantCreate {
  return {
    name: values.name,
    species_id: values.species_id || null,
    species_name: values.species_name || null,
    scientific_name: values.scientific_name || null,
    location_id: values.location_id || null,
    notes: values.notes || null,
    tags: values.tags
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean),
  };
}

interface PlantFormProps {
  initial?: PlantDetail;
  submitLabel: string;
  busy: boolean;
  onSubmit: (payload: PlantCreate) => void;
}

export function PlantForm({ initial, submitLabel, busy, onSubmit }: PlantFormProps) {
  const { data: locations = [] } = useLocations();
  const { data: speciesList = [] } = useSpecies();
  const createSpecies = useCreateSpecies();
  const [newSpeciesOpen, setNewSpeciesOpen] = useState(false);
  const form = useForm<PlantFormValues>({
    resolver: zodResolver(plantFormSchema),
    defaultValues: {
      name: initial?.name ?? '',
      species_id: initial?.species_id ?? '',
      species_name: initial?.species_name ?? '',
      scientific_name: initial?.scientific_name ?? '',
      location_id: initial?.location_id ?? '',
      notes: initial?.notes ?? '',
      tags: initial?.tags.join(', ') ?? '',
    },
  });
  const speciesId = form.watch('species_id');

  return (
    <>
      <form
        className="flex flex-col gap-4"
        onSubmit={form.handleSubmit((values) => onSubmit(toPlantPayload(values)))}
      >
        <div>
          <label className="mb-1 block text-sm font-medium">Name</label>
          <input className="input-base" placeholder="My Monstera" {...form.register('name')} />
          {form.formState.errors.name && (
            <p className="mt-1 text-sm text-red-600">{form.formState.errors.name.message}</p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Species</label>
          <div className="flex gap-2">
            <select className="input-base" aria-label="Species" {...form.register('species_id')}>
              <option value="">No species</option>
              {speciesList.map((species) => (
                <option key={species.id} value={species.id}>
                  {species.name}
                  {species.scientific_name ? ` (${species.scientific_name})` : ''}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-secondary shrink-0"
              title="Create a new species"
              onClick={() => setNewSpeciesOpen(true)}
            >
              <Plus className="h-4 w-4" />
              New
            </button>
          </div>
          {!initial && speciesId && (
            <p className="mt-1 text-xs text-stone-500">
              The species&apos; default care reminders are added automatically.
            </p>
          )}
        </div>

        {/* Free-text fallback for plants that aren't worth a species entry. */}
        {!speciesId && (
          <>
            <div>
              <label className="mb-1 block text-sm font-medium">Species (free text)</label>
              <input className="input-base" placeholder="Monstera" {...form.register('species_name')} />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium">Scientific name</label>
              <input className="input-base" placeholder="Monstera deliciosa" {...form.register('scientific_name')} />
            </div>
          </>
        )}

        <div>
          <label className="mb-1 block text-sm font-medium">Location</label>
          <select className="input-base" aria-label="Location" {...form.register('location_id')}>
            <option value="">No location</option>
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Tags (comma-separated)</label>
          <input className="input-base" placeholder="tropical, low-light" {...form.register('tags')} />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Notes</label>
          <textarea className="input-base" rows={3} {...form.register('notes')} />
        </div>

        <button type="submit" className="btn-primary self-start" disabled={busy}>
          {submitLabel}
        </button>
      </form>

      {/* Sibling of the form: nesting a <form> inside a <form> is invalid HTML. */}
      <Modal title="New species" open={newSpeciesOpen} onClose={() => setNewSpeciesOpen(false)}>
        <SpeciesForm
          submitLabel="Create species"
          busy={createSpecies.isPending}
          onSubmit={(payload) => {
            createSpecies.mutate(payload, {
              onSuccess: (created) => {
                form.setValue('species_id', created.id);
                setNewSpeciesOpen(false);
              },
            });
          }}
        />
      </Modal>
    </>
  );
}
