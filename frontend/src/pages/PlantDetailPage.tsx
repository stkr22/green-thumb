import { useState } from 'react';
import { useSuspenseQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router';
import { Leaf, MapPin, Pencil, Trash2 } from 'lucide-react';

import { photoUrl } from '../api/client';
import { useCreateLog } from '../api/hooks/useLogs';
import { useDeletePlant, usePlant, useUpdatePlant } from '../api/hooks/usePlants';
import { locationsQuery } from '../api/queries';
import type { PlantDetail } from '../api/types';
import { Field } from '../components/Field';
import { GrowthJournal } from '../components/GrowthJournal';
import { Modal } from '../components/Modal';
import { PlantForm } from '../components/PlantForm';
import { useToast } from '../components/Toast';
import { CareActions } from '../components/plant/CareActions';
import { CareGuide } from '../components/plant/CareGuide';
import { CareLogTimeline } from '../components/plant/CareLogTimeline';
import { PhotoGallery } from '../components/plant/PhotoGallery';
import { RemindersSection } from '../components/plant/RemindersSection';

function speciesLine(plant: PlantDetail): string {
  const name = plant.species?.name ?? plant.species_name;
  const scientific = plant.species?.scientific_name ?? plant.scientific_name;
  return [name, scientific].filter(Boolean).join(' · ');
}

function CustomLogForm({ plantId, onDone }: { plantId: string; onDone: () => void }) {
  const createLog = useCreateLog(plantId);
  const { notify } = useToast();
  const [eventType, setEventType] = useState('');
  const [notes, setNotes] = useState('');

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        const type = eventType.trim();
        if (!type) return;
        createLog.mutate(
          { event_type: type, notes: notes || null },
          {
            onSuccess: () => {
              notify(`${type} logged`);
              onDone();
            },
          },
        );
      }}
    >
      <Field label="Event type">
        {(id) => (
          <input
            id={id}
            className="input-base"
            placeholder="misting, pruning, …"
            required
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
          />
        )}
      </Field>
      <Field label="Notes (optional)">
        {(id) => (
          <textarea id={id} className="input-base" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        )}
      </Field>
      <button type="submit" className="btn-primary self-start" disabled={createLog.isPending}>
        Log event
      </button>
    </form>
  );
}

export function PlantDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { notify } = useToast();
  // Both awaited by the route loader; a missing plant ends up on RouteError.
  const { data: plant } = usePlant(id);
  const { data: locations } = useSuspenseQuery(locationsQuery);
  const updatePlant = useUpdatePlant(id);
  const deletePlant = useDeletePlant();
  const [editOpen, setEditOpen] = useState(false);
  const [customLogOpen, setCustomLogOpen] = useState(false);

  const locationName = locations.find((location) => location.id === plant.location_id)?.name;
  const species = speciesLine(plant);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div className="card overflow-hidden">
        {plant.cover_photo_id ? (
          <img src={photoUrl(plant.cover_photo_id)} alt={plant.name} className="h-64 w-full object-cover" />
        ) : (
          <div className="flex h-40 items-center justify-center bg-emerald-50">
            <Leaf className="h-12 w-12 text-emerald-300" />
          </div>
        )}
        <div className="p-5">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">{plant.name}</h1>
              {species && <p className="italic text-stone-500">{species}</p>}
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-stone-500">
                {locationName && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-4 w-4" />
                    {locationName}
                  </span>
                )}
                {plant.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-stone-100 px-2 py-0.5 text-xs">
                    {tag}
                  </span>
                ))}
              </div>
              {plant.notes && <p className="mt-3 text-sm text-stone-600">{plant.notes}</p>}
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary" onClick={() => setEditOpen(true)}>
                <Pencil className="h-4 w-4" />
                Edit
              </button>
              <button
                type="button"
                className="btn-danger"
                aria-label={`Delete ${plant.name}`}
                onClick={() => {
                  if (window.confirm(`Delete ${plant.name} including photos, logs and reminders?`)) {
                    deletePlant.mutate(plant.id, {
                      onSuccess: () => {
                        notify(`${plant.name} deleted`);
                        navigate('/plants');
                      },
                    });
                  }
                }}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="mt-5">
            <CareActions plant={plant} onCustom={() => setCustomLogOpen(true)} />
          </div>
        </div>
      </div>

      <CareGuide plant={plant} />
      <PhotoGallery plantId={plant.id} coverPhotoId={plant.cover_photo_id} />
      <GrowthJournal plantId={plant.id} />
      <CareLogTimeline plantId={plant.id} />
      <RemindersSection plantId={plant.id} />

      <Modal title={`Edit ${plant.name}`} open={editOpen} onClose={() => setEditOpen(false)}>
        <PlantForm
          initial={plant}
          submitLabel="Save changes"
          busy={updatePlant.isPending}
          onSubmit={(payload) => updatePlant.mutate(payload, { onSuccess: () => setEditOpen(false) })}
        />
      </Modal>

      <Modal title="Log custom care event" open={customLogOpen} onClose={() => setCustomLogOpen(false)}>
        <CustomLogForm plantId={plant.id} onDone={() => setCustomLogOpen(false)} />
      </Modal>
    </div>
  );
}
