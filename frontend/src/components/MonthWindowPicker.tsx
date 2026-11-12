// Start/end month selects for "only in these months" care (repotting in
// spring). Used by the per-plant reminder form and the species default plan.

import { Field } from './Field';
import { MONTHS, type MonthWindow } from '../lib/seasons';

interface MonthWindowPickerProps {
  value: MonthWindow | null;
  onChange: (value: MonthWindow | null) => void;
  /** Prefix for the accessible names, e.g. "Repotting window". */
  name: string;
  startLabel: string;
  endLabel: string;
  anyLabel: string;
}

function MonthOptions() {
  return MONTHS.map((label, index) => (
    <option key={label} value={index + 1}>
      {label}
    </option>
  ));
}

export function MonthWindowPicker({ value, onChange, name, startLabel, endLabel, anyLabel }: MonthWindowPickerProps) {
  return (
    <>
      <Field label={startLabel} size="sm">
        {(id) => (
          <select
            id={id}
            aria-label={`${name} start`}
            className="input-base w-32"
            value={value ? value[0] : ''}
            onChange={(event) => {
              const month = Number.parseInt(event.target.value, 10);
              // Default the end to the start so a half-set window can never be
              // submitted; the API rejects those outright.
              onChange(month > 0 ? [month, value?.[1] ?? month] : null);
            }}
          >
            <option value="">{anyLabel}</option>
            <MonthOptions />
          </select>
        )}
      </Field>
      {value && (
        <Field label={endLabel} size="sm">
          {(id) => (
            <select
              id={id}
              aria-label={`${name} end`}
              className="input-base w-32"
              value={value[1]}
              onChange={(event) => onChange([value[0], Number.parseInt(event.target.value, 10)])}
            >
              <MonthOptions />
            </select>
          )}
        </Field>
      )}
    </>
  );
}
