// Shared create/edit species form (React Hook Form + Zod). The default care
// plan is entered as one interval per common event type; empty means "no
// default reminder for that event".

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import type { SpeciesCreate, SpeciesRead } from '../api/types';

const INTERVAL_FIELDS = [
  { key: 'watering_days', eventType: 'watering', label: 'Watering' },
  { key: 'fertilising_days', eventType: 'fertilising', label: 'Fertilising' },
  { key: 'repotting_days', eventType: 'repotting', label: 'Repotting' },
] as const;

const speciesFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  scientific_name: z.string(),
  light: z.string(),
  watering_hint: z.string(),
  soil_hint: z.string(),
  deadheading: z.boolean(),
  deadheading_hint: z.string(),
  toxicity: z.string(),
  common_issues: z.string(),
  watering_days: z.string(),
  fertilising_days: z.string(),
  repotting_days: z.string(),
});

type SpeciesFormValues = z.infer<typeof speciesFormSchema>;

function toSpeciesPayload(values: SpeciesFormValues): SpeciesCreate {
  const default_intervals: Record<string, number> = {};
  for (const { key, eventType } of INTERVAL_FIELDS) {
    const days = Number.parseInt(values[key], 10);
    if (days > 0) default_intervals[eventType] = days;
  }
  return {
    name: values.name,
    scientific_name: values.scientific_name || null,
    light: values.light || null,
    watering_hint: values.watering_hint || null,
    soil_hint: values.soil_hint || null,
    deadheading: values.deadheading,
    deadheading_hint: values.deadheading_hint || null,
    toxicity: values.toxicity || null,
    common_issues: values.common_issues || null,
    default_intervals,
  };
}

interface SpeciesFormProps {
  initial?: SpeciesRead;
  submitLabel: string;
  busy: boolean;
  onSubmit: (payload: SpeciesCreate) => void;
}

export function SpeciesForm({ initial, submitLabel, busy, onSubmit }: SpeciesFormProps) {
  const form = useForm<SpeciesFormValues>({
    resolver: zodResolver(speciesFormSchema),
    defaultValues: {
      name: initial?.name ?? '',
      scientific_name: initial?.scientific_name ?? '',
      light: initial?.light ?? '',
      watering_hint: initial?.watering_hint ?? '',
      soil_hint: initial?.soil_hint ?? '',
      deadheading: initial?.deadheading ?? false,
      deadheading_hint: initial?.deadheading_hint ?? '',
      toxicity: initial?.toxicity ?? '',
      common_issues: initial?.common_issues ?? '',
      watering_days: initial?.default_intervals.watering?.toString() ?? '',
      fertilising_days: initial?.default_intervals.fertilising?.toString() ?? '',
      repotting_days: initial?.default_intervals.repotting?.toString() ?? '',
    },
  });
  const needsDeadheading = form.watch('deadheading');

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={form.handleSubmit((values) => onSubmit(toSpeciesPayload(values)))}
    >
      <div>
        <label className="mb-1 block text-sm font-medium">Name</label>
        <input className="input-base" placeholder="Monstera" {...form.register('name')} />
        {form.formState.errors.name && (
          <p className="mt-1 text-sm text-red-600">{form.formState.errors.name.message}</p>
        )}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Scientific name</label>
        <input className="input-base" placeholder="Monstera deliciosa" {...form.register('scientific_name')} />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Light</label>
        <input className="input-base" placeholder="Bright indirect" {...form.register('light')} />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Watering advice</label>
        <input
          className="input-base"
          placeholder="Let the top few centimetres of soil dry out"
          {...form.register('watering_hint')}
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Soil & repotting advice</label>
        <input className="input-base" placeholder="Well-draining aroid mix" {...form.register('soil_hint')} />
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" {...form.register('deadheading')} />
          Needs deadheading
        </label>
        {needsDeadheading && (
          <input
            className="input-base mt-2"
            placeholder="Pinch spent blooms just above the next bud"
            {...form.register('deadheading_hint')}
          />
        )}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Toxicity</label>
        <input className="input-base" placeholder="Toxic to cats and dogs" {...form.register('toxicity')} />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium">Common issues</label>
        <textarea
          className="input-base"
          rows={3}
          placeholder={'Spider mites: fine webbing under leaves\nRoot rot: mushy stems after overwatering'}
          {...form.register('common_issues')}
        />
      </div>

      <fieldset>
        <legend className="mb-1 text-sm font-medium">Default care plan (every N days)</legend>
        <p className="mb-2 text-xs text-stone-500">
          New plants of this species get these reminders automatically; leave a field empty to skip it.
        </p>
        <div className="flex flex-wrap gap-3">
          {INTERVAL_FIELDS.map(({ key, label }) => (
            <div key={key}>
              <label className="mb-1 block text-xs text-stone-500">{label}</label>
              <input
                type="number"
                min={1}
                max={3650}
                aria-label={`${label} interval`}
                className="input-base w-28"
                {...form.register(key)}
              />
            </div>
          ))}
        </div>
      </fieldset>

      <button type="submit" className="btn-primary self-start" disabled={busy}>
        {submitLabel}
      </button>
    </form>
  );
}
