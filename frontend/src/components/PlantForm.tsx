// Shared create/edit plant form (React Hook Form + Zod). Tags are entered as a
// comma-separated string and converted on submit.

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import { useLocations } from '../api/hooks/useLocations';
import type { PlantCreate, PlantDetail } from '../api/types';

const plantFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
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
  const form = useForm<PlantFormValues>({
    resolver: zodResolver(plantFormSchema),
    defaultValues: {
      name: initial?.name ?? '',
      species_name: initial?.species_name ?? '',
      scientific_name: initial?.scientific_name ?? '',
      location_id: initial?.location_id ?? '',
      notes: initial?.notes ?? '',
      tags: initial?.tags.join(', ') ?? '',
    },
  });

  return (
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
        <input className="input-base" placeholder="Monstera" {...form.register('species_name')} />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Scientific name</label>
        <input className="input-base" placeholder="Monstera deliciosa" {...form.register('scientific_name')} />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Location</label>
        <select className="input-base" {...form.register('location_id')}>
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
  );
}
