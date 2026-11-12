// A label tied to its control via a generated id. Without htmlFor/id the label
// is just text: screen readers announce an unnamed field and clicking the label
// doesn't focus the input.

import { useId } from 'react';
import type { ReactNode } from 'react';

interface FieldProps {
  label: ReactNode;
  /** Render prop receiving the id to put on the control. */
  children: (id: string) => ReactNode;
  error?: string;
  hint?: ReactNode;
  /** 'sm' is the compact style used in inline rows (reminder form, editors). */
  size?: 'md' | 'sm';
  className?: string;
}

export function Field({ label, children, error, hint, size = 'md', className }: FieldProps) {
  const id = useId();
  const labelClass = size === 'sm' ? 'mb-1 block text-xs text-stone-500' : 'mb-1 block text-sm font-medium';
  return (
    <div className={className}>
      <label htmlFor={id} className={labelClass}>
        {label}
      </label>
      {children(id)}
      {hint && <p className="mt-1 text-xs text-stone-500">{hint}</p>}
      {error && (
        <p role="alert" className="mt-1 text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
