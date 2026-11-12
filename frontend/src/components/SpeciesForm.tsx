// Shared create/edit species form (React Hook Form + Zod). The default care
// plan is entered as one interval per common event type; empty means "no
// default reminder for that event".
//
// The season plan is held in plain state rather than RHF: its cells are
// derived from the interval fields (days at a season's pace) and carry a
// paused state, which does not map onto a flat validated text field.

import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
// zod/mini: same validation, tree-shakable functional API, much smaller bundle.
import { z } from 'zod/mini';

import { useSeasonInfo } from '../api/hooks/useSeasons';
import type { SpeciesCreate, SpeciesRead } from '../api/types';
import { careEventStyle } from '../lib/careEvents';
import { Field } from './Field';
import { MonthWindowPicker } from './MonthWindowPicker';
import {
  type MonthWindow,
  SEASONAL_EVENT_TYPES,
  SEASONS,
  type SeasonPlan,
  WINDOWED_EVENT_TYPES,
  daysToMultiplier,
  isNeutral,
  seasonDays,
  windowLabel,
} from '../lib/seasons';

type WindowDraft = Record<string, MonthWindow | undefined>;

const INTERVAL_FIELDS = [
  { key: 'watering_days', eventType: 'watering', label: 'Watering' },
  { key: 'fertilising_days', eventType: 'fertilising', label: 'Fertilising' },
  { key: 'repotting_days', eventType: 'repotting', label: 'Repotting' },
] as const;

/** Base interval per event type with an interval field; 0 means "not set". */
type BaseDays = Record<(typeof INTERVAL_FIELDS)[number]['eventType'], number>;

// Kept as strings (that's what the inputs hold) but validated, so a typo like
// "-3" or "1e4" is reported instead of silently dropping the reminder.
const intervalDays = z.string().check(
  z.trim(),
  z.refine((value) => value === '' || (/^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 3650), {
    message: 'Enter 1–3650 days, or leave empty',
  }),
);

const speciesFormSchema = z.object({
  name: z.string().check(z.minLength(1, 'Name is required'), z.maxLength(200)),
  scientific_name: z.string(),
  light: z.string(),
  watering_hint: z.string(),
  soil_hint: z.string(),
  deadheading: z.boolean(),
  deadheading_hint: z.string(),
  toxicity: z.string(),
  common_issues: z.string(),
  watering_days: intervalDays,
  fertilising_days: intervalDays,
  repotting_days: intervalDays,
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
    const multipliers = plan[eventType];
    if (default_intervals[eventType] && multipliers && !isNeutral(multipliers)) {
      season_plan[eventType] = multipliers;
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
  baseDays: BaseDays;
}) {
  const { data: seasonInfo } = useSeasonInfo();
  const configurable = SEASONAL_EVENT_TYPES.filter((eventType) => baseDays[eventType] > 0);

  function setCell(eventType: string, season: string, multiplier: number | null | undefined) {
    const cells = { ...plan[eventType] };
    if (multiplier === undefined) delete cells[season];
    else cells[season] = multiplier;
    setPlan({ ...plan, [eventType]: cells });
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
  baseDays: BaseDays;
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
                const [start, end] = seasonInfo.season_months[key] ?? [];
                if (start === undefined || end === undefined) return null;
                return (
                  <button
                    key={key}
                    type="button"
                    className="btn-secondary mb-2 px-2 py-1 text-xs"
                    onClick={() => setWindows({ ...windows, [eventType]: [start, end] })}
                  >
                    {label}
                  </button>
                );
              })}
            <MonthWindowPicker
              value={window ?? null}
              onChange={(value) => setWindows({ ...windows, [eventType]: value ?? undefined })}
              name={`${style.label} window`}
              startLabel="From"
              endLabel="To"
              anyLabel="Any time"
            />
            {window && (
              <p className="mb-2 text-xs text-stone-500">
                due dates wait for {windowLabel(window[0], window[1])}
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
    const [start, end] = months;
    if (months.length === 2 && start !== undefined && end !== undefined) draft[eventType] = [start, end];
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
  // useWatch subscribes to just these fields; watch() at the top would
  // re-render the whole form (and both editors) on every keystroke anywhere.
  const [needsDeadheading, wateringDays, fertilisingDays, repottingDays] = useWatch({
    control: form.control,
    name: ['deadheading', 'watering_days', 'fertilising_days', 'repotting_days'],
  });
  const baseDays: BaseDays = {
    watering: Number.parseInt(wateringDays, 10) || 0,
    fertilising: Number.parseInt(fertilisingDays, 10) || 0,
    repotting: Number.parseInt(repottingDays, 10) || 0,
  };
  const errors = form.formState.errors;

  return (
    <form
      className="flex flex-col gap-4"
      // Zod is the one validation path, rendering inline messages; native
      // min/max bubbles would block submit before it ever ran.
      noValidate
      onSubmit={form.handleSubmit((values) => onSubmit(toSpeciesPayload(values, plan, windows)))}
    >
      <Field label="Name" error={errors.name?.message}>
        {(id) => <input id={id} className="input-base" placeholder="Monstera" {...form.register('name')} />}
      </Field>

      <Field label="Scientific name">
        {(id) => (
          <input id={id} className="input-base" placeholder="Monstera deliciosa" {...form.register('scientific_name')} />
        )}
      </Field>

      <Field label="Light">
        {(id) => <input id={id} className="input-base" placeholder="Bright indirect" {...form.register('light')} />}
      </Field>

      <Field label="Watering advice">
        {(id) => (
          <input
            id={id}
            className="input-base"
            placeholder="Let the top few centimetres of soil dry out"
            {...form.register('watering_hint')}
          />
        )}
      </Field>

      <Field label="Soil & repotting advice">
        {(id) => (
          <input id={id} className="input-base" placeholder="Well-draining aroid mix" {...form.register('soil_hint')} />
        )}
      </Field>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" {...form.register('deadheading')} />
          Needs deadheading
        </label>
        {needsDeadheading && (
          <input
            className="input-base mt-2"
            aria-label="Deadheading advice"
            placeholder="Pinch spent blooms just above the next bud"
            {...form.register('deadheading_hint')}
          />
        )}
      </div>

      <Field label="Toxicity">
        {(id) => (
          <input id={id} className="input-base" placeholder="Toxic to cats and dogs" {...form.register('toxicity')} />
        )}
      </Field>

      <Field label="Common issues">
        {(id) => (
          <textarea
            id={id}
            className="input-base"
            rows={3}
            placeholder={'Spider mites: fine webbing under leaves\nRoot rot: mushy stems after overwatering'}
            {...form.register('common_issues')}
          />
        )}
      </Field>

      <fieldset>
        <legend className="mb-1 text-sm font-medium">Default care plan (every N days)</legend>
        <p className="mb-2 text-xs text-stone-500">
          New plants of this species get these reminders automatically; leave a field empty to skip it.
        </p>
        <div className="flex flex-wrap gap-3">
          {INTERVAL_FIELDS.map(({ key, label }) => (
            <Field key={key} label={label} size="sm" error={errors[key]?.message}>
              {(id) => (
                <input
                  id={id}
                  type="number"
                  min={1}
                  max={3650}
                  // Deliberately "<event> interval": the season cells below are
                  // named "<event> in <season>", and role-name matching is
                  // substring-based, so plain "<event>" would match those too.
                  aria-label={`${label} interval`}
                  className="input-base w-28"
                  {...form.register(key)}
                />
              )}
            </Field>
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
