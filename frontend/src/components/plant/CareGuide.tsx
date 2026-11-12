import { BellPlus, Droplets, Scissors, Shovel, Sprout, Sun, TriangleAlert } from 'lucide-react';

import { useApplySpeciesDefaults } from '../../api/hooks/usePlants';
import type { PlantDetail } from '../../api/types';
import { useToast } from '../Toast';

export function CareGuide({ plant }: { plant: PlantDetail }) {
  const applyDefaults = useApplySpeciesDefaults(plant.id);
  const { notify } = useToast();
  const species = plant.species;
  if (!species) return null;

  const hints = [
    { icon: Sun, label: 'Light', value: species.light },
    { icon: Droplets, label: 'Watering', value: species.watering_hint },
    { icon: Shovel, label: 'Soil & repotting', value: species.soil_hint },
    {
      icon: Scissors,
      label: 'Deadheading',
      value: species.deadheading ? (species.deadheading_hint ?? 'Remove spent blooms regularly') : null,
    },
    { icon: TriangleAlert, label: 'Toxicity', value: species.toxicity },
  ].filter((hint) => hint.value);
  const hasDefaults = Object.keys(species.default_intervals).length > 0;
  if (hints.length === 0 && !species.common_issues && !hasDefaults) return null;

  return (
    <section className="card p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold">
          <Sprout className="h-4 w-4 text-emerald-600" />
          Care guide
          <span className="text-sm font-normal italic text-stone-500">{species.name}</span>
        </h2>
        {hasDefaults && (
          <button
            type="button"
            className="btn-secondary"
            disabled={applyDefaults.isPending}
            onClick={() =>
              applyDefaults.mutate(undefined, {
                onSuccess: (created) =>
                  notify(
                    created.length > 0
                      ? `${created.length} reminder${created.length === 1 ? '' : 's'} added`
                      : 'All default reminders already exist',
                  ),
              })
            }
          >
            <BellPlus className="h-4 w-4" />
            Apply default care plan
          </button>
        )}
      </div>
      {hints.length > 0 && (
        <dl className="grid gap-3 sm:grid-cols-2">
          {hints.map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-start gap-2">
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
              <div>
                <dt className="text-sm font-medium">{label}</dt>
                <dd className="text-sm text-stone-600">{value}</dd>
              </div>
            </div>
          ))}
        </dl>
      )}
      {species.common_issues && (
        <div className={hints.length > 0 ? 'mt-4' : ''}>
          <h3 className="mb-1 text-sm font-medium">Common issues & how to spot them</h3>
          <p className="whitespace-pre-line text-sm text-stone-600">{species.common_issues}</p>
        </div>
      )}
    </section>
  );
}
