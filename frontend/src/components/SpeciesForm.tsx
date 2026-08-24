// Shared create/edit species form (React Hook Form + Zod). The default care
// plan is entered as one interval per common event type; empty means "no
// default reminder for that event".
//
// The season plan is held in plain state rather than RHF: its cells are
// derived from the interval fields (days at a season's pace) and carry a
// paused state, which does not map onto a flat validated text field.

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import { useSeasonInfo } from '../api/hooks/useSeasons';
import type { SpeciesCreate, SpeciesRead } from '../api/types';
import { careEventStyle } from '../lib/careEvents';
import {
  MONTHS,
  type MonthWindow,
  SEASONAL_EVENT_TYPES,
  SEASONS,
  type SeasonPlan,
  WINDOWED_EVENT_TYPES,
  daysToMultiplier,
  isNeutral,
  monthLabel,
  seasonDays,
} from '../lib/seasons';

type WindowDraft = Record<string, MonthWindow | undefined>;

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

function toSpeciesPayload(values: SpeciesFormValues, plan: SeasonPlan, windows: WindowDraft): SpeciesCreate {
  const default_intervals: Record<string, number> = {};
  for (const { key, eventType } of INTERVAL_FIELDS) {
    const days = Number.parseInt(values[key], 10);
    if (days > 0) default_intervals[eventType] = days;
  }
  // Only keep entries that actually change something, so a species nobody
  // configured seasonally stores an empty plan rather than a wall of 1.0s.
  const season_plan: SeasonPlan = {};
  for (const eventType of SEASONAL_EVENT_TYPES) {
    if (default_intervals[eventType] && !isNeutral(plan[eventType])) {
      season_plan[eventType] = plan[eventType];
    }
  }
  const default_windows: Record<string, number[]> = {};
  for (const eventType of WINDOWED_EVENT_TYPES) {
    const window = windows[eventType];
    if (default_intervals[eventType] && window) default_windows[eventType] = window;
  }
  return {
    season_plan,
    default_windows,
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

function SeasonPlanEditor({
  plan,
  setPlan,
  baseDays,
}: {
  plan: SeasonPlan;
  setPlan: (plan: SeasonPlan) => void;
  baseDays: Record<string, number>;
}) {
  const { data: seasonInfo } = useSeasonInfo();
  const configurable = SEASONAL_EVENT_TYPES.filter((eventType) => baseDays[eventType] > 0);

  function setCell(eventType: string, season: string, multiplier: number | null | undefined) {
    const next = { ...plan, [eventType]: { ...plan[eventType] } };
    if (multiplier === undefined) delete next[eventType][season];
    else next[eventType][season] = multiplier;
    setPlan(next);
  }

  if (configurable.length === 0) {
    return (
      <p className="text-xs text-stone-500">
        Set a watering or fertilising interval above to give this species a seasonal pace.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {seasonInfo && seasonInfo.presets.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-stone-500">Start from:</span>
          {seasonInfo.presets.map((preset) => (
            <button
              key={preset.key}
              type="button"
              className="btn-secondary px-2 py-1 text-xs"
              onClick={() => setPlan(preset.plan as SeasonPlan)}
            >
              {preset.key.replace('_', ' ')}
            </button>
          ))}
          <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => setPlan({})}>
            no seasonal change
          </button>
        </div>
      )}

      {configurable.map((eventType) => {
        const base = baseDays[eventType];
        const style = careEventStyle(eventType);
        return (
          <div key={eventType}>
            <p className="mb-1 text-xs font-medium text-stone-600">{style.label}</p>
            <div className="flex flex-wrap gap-3">
              {SEASONS.map(({ key, label }) => {
                const multiplier = plan[eventType]?.[key];
                const paused = multiplier === null;
                const days = seasonDays(base, multiplier);
                return (
                  <div key={key} className="w-24">
                    <label className="mb-1 block text-xs text-stone-500" htmlFor={`${eventType}-${key}`}>
                      {label}
                      {seasonInfo?.current_season === key && ' ·  now'}
                    </label>
                    <input
                      id={`${eventType}-${key}`}
                      type="number"
                      min={1}
                      max={3650}
                      disabled={paused}
                      // Deliberately not "<event> interval in <season>": getByRole name
                      // matching is substring-based, and that would collide with the
                      // "<event> interval" base field above.
                      aria-label={`${style.label} in ${label}`}
                      className="input-base w-full disabled:bg-stone-100 disabled:text-stone-400"
                      value={days ?? ''}
                      placeholder="paused"
                      onChange={(event) => {
                        const value = Number.parseInt(event.target.value, 10);
                        setCell(eventType, key, value > 0 ? daysToMultiplier(base, value) : undefined);
                      }}
                    />
                    <label className="mt-1 flex items-center gap-1 text-xs text-stone-500">
                      <input
                        type="checkbox"
                        checked={paused}
                        aria-label={`Pause ${style.label} in ${label}`}
                        onChange={(event) => setCell(eventType, key, event.target.checked ? null : undefined)}
                      />
                      pause
                    </label>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Month bounds for care that may only happen at one time of year (repotting in spring). */
function WindowEditor({
  windows,
  setWindows,
  baseDays,
}: {
  windows: WindowDraft;
  setWindows: (windows: WindowDraft) => void;
  baseDays: Record<string, number>;
}) {
  const { data: seasonInfo } = useSeasonInfo();
  const configurable = WINDOWED_EVENT_TYPES.filter((eventType) => baseDays[eventType] > 0);
  if (configurable.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      {configurable.map((eventType) => {
        const style = careEventStyle(eventType);
        const window = windows[eventType];
        return (
          <div key={eventType} className="flex flex-wrap items-end gap-2">
            <span className="mb-2 text-xs font-medium text-stone-600">{style.label}</span>
            {/* Which months a season covers depends on the hemisphere, so the
                server supplies the mapping rather than the frontend assuming. */}
            {seasonInfo &&
              SEASONS.map(({ key, label }) => {
                const months = seasonInfo.season_months[key];
                if (!months) return null;
                return (
                  <button
                    key={key}
                    type="button"
                    className="btn-secondary mb-2 px-2 py-1 text-xs"
                    onClick={() => setWindows({ ...windows, [eventType]: [months[0], months[1]] })}
                  >
                    {label}
                  </button>
                );
              })}
            <div>
              <label className="mb-1 block text-xs text-stone-500" htmlFor={`${eventType}-window-start`}>
                From
              </label>
              <select
                id={`${eventType}-window-start`}
                aria-label={`${style.label} window start`}
                className="input-base w-28"
                value={window ? window[0] : ''}
                onChange={(event) => {
                  const month = Number.parseInt(event.target.value, 10);
                  setWindows({
                    ...windows,
                    // Default the end month to the start so a half-set window is
                    // never submitted; the API rejects those outright.
                    [eventType]: month > 0 ? [month, window?.[1] ?? month] : undefined,
                  });
                }}
              >
                <option value="">Any time</option>
                {MONTHS.map((label, index) => (
                  <option key={label} value={index + 1}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            {window && (
              <div>
                <label className="mb-1 block text-xs text-stone-500" htmlFor={`${eventType}-window-end`}>
                  To
                </label>
                <select
                  id={`${eventType}-window-end`}
                  aria-label={`${style.label} window end`}
                  className="input-base w-28"
                  value={window[1]}
                  onChange={(event) =>
                    setWindows({ ...windows, [eventType]: [window[0], Number.parseInt(event.target.value, 10)] })
                  }
                >
                  {MONTHS.map((label, index) => (
                    <option key={label} value={index + 1}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {window && (
              <p className="mb-2 text-xs text-stone-500">
                due dates wait for {monthLabel(window[0])}–{monthLabel(window[1])}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function initialWindows(species: SpeciesRead | undefined): WindowDraft {
  const draft: WindowDraft = {};
  for (const [eventType, months] of Object.entries(species?.default_windows ?? {})) {
    if (months.length === 2) draft[eventType] = [months[0], months[1]];
  }
  return draft;
}

export function SpeciesForm({ initial, submitLabel, busy, onSubmit }: SpeciesFormProps) {
  const [plan, setPlan] = useState<SeasonPlan>((initial?.season_plan as SeasonPlan) ?? {});
  const [windows, setWindows] = useState<WindowDraft>(() => initialWindows(initial));
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
  const baseDays: Record<string, number> = {
    watering: Number.parseInt(form.watch('watering_days'), 10) || 0,
    fertilising: Number.parseInt(form.watch('fertilising_days'), 10) || 0,
    repotting: Number.parseInt(form.watch('repotting_days'), 10) || 0,
  };

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={form.handleSubmit((values) => onSubmit(toSpeciesPayload(values, plan, windows)))}
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

      <fieldset>
        <legend className="mb-1 text-sm font-medium">Seasonal pace</legend>
        <p className="mb-2 text-xs text-stone-500">
          The intervals above are the growing-season pace. Set what each season should be instead, or pause an
          event type for seasons when the plant is resting.
        </p>
        <SeasonPlanEditor plan={plan} setPlan={setPlan} baseDays={baseDays} />
      </fieldset>

      {baseDays.repotting > 0 && (
        <fieldset>
          <legend className="mb-1 text-sm font-medium">Time of year</legend>
          <p className="mb-2 text-xs text-stone-500">
            For jobs that belong in one part of the year. The interval keeps running at full speed — only the due
            date waits for these months.
          </p>
          <WindowEditor windows={windows} setWindows={setWindows} baseDays={baseDays} />
        </fieldset>
      )}

      <button type="submit" className="btn-primary self-start" disabled={busy}>
        {submitLabel}
      </button>
    </form>
  );
}
