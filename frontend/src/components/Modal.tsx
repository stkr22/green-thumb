// Native <dialog> opened with showModal(): the browser supplies the focus
// trap, Escape handling, an inert background and focus restoration on close,
// which a hand-rolled overlay has to reimplement (and usually gets partly wrong).

import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}

export function Modal({ title, open, onClose, children }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className="card m-auto w-[calc(100%-2rem)] max-w-lg p-0 backdrop:bg-black/40"
      // Escape fires "cancel"; route it through onClose so React state stays
      // the source of truth for whether the dialog is open.
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      // The inner wrapper fills the dialog, so a click whose target is the
      // dialog itself can only have landed on the backdrop.
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      {/* Children mount only while open, so forms start fresh each time. */}
      {open && (
        <div className="max-h-[90dvh] overflow-y-auto p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 id={titleId} className="text-lg font-semibold">
              {title}
            </h2>
            <button type="button" aria-label="Close" onClick={onClose} className="text-stone-400 hover:text-stone-700">
              <X className="h-5 w-5" />
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}
