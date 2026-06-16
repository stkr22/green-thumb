import { useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Camera, Droplets, FlaskConical, Leaf, MapPin, Pencil, Plus, Shovel, Star, Trash2 } from 'lucide-react';

import { photoUrl, thumbnailUrl } from '../api/client';
import { useLocations } from '../api/hooks/useLocations';
import { LOGS_PAGE_SIZE, useCreateLog, useDeleteLog, useLogs } from '../api/hooks/useLogs';
import { useDeletePhoto, usePhotos, useUploadPhoto } from '../api/hooks/usePhotos';
import { useDeletePlant, usePlant, useSetCoverPhoto, useUpdatePlant } from '../api/hooks/usePlants';
import { useCreateReminder, useDeleteReminder, useReminders, useUpdateReminder } from '../api/hooks/useReminders';
import type { PlantDetail } from '../api/types';
import { Modal } from '../components/Modal';
import { PlantForm } from '../components/PlantForm';
import { useToast } from '../components/Toast';
import { formatDateTime, formatDaysAgo } from '../lib/dates';

const QUICK_ACTIONS = [
  { eventType: 'watering', label: 'Water', icon: Droplets },
  { eventType: 'fertilising', label: 'Fertilise', icon: FlaskConical },
  { eventType: 'repotting', label: 'Repot', icon: Shovel },
];

function CareSummary({ plant }: { plant: PlantDetail }) {
  return (
    <div className="flex flex-wrap gap-4">
      {QUICK_ACTIONS.map(({ eventType, label, icon: Icon }) => (
        <div key={eventType} className="card flex items-center gap-3 px-4 py-3">
          <Icon className="h-5 w-5 text-emerald-600" />
          <div>
            <p className="text-sm font-medium">{label}ed</p>
            <p className="text-sm text-stone-500">{formatDaysAgo(plant.last_events?.[eventType])}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function PhotoGallery({ plantId, coverPhotoId }: { plantId: string; coverPhotoId: string | null }) {
  const { data: photos = [] } = usePhotos(plantId);
  const uploadPhoto = useUploadPhoto(plantId);
  const deletePhoto = useDeletePhoto(plantId);
  const setCover = useSetCoverPhoto(plantId);
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <section className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold">Photos</h2>
        <button
          type="button"
          className="btn-secondary"
          disabled={uploadPhoto.isPending}
          onClick={() => fileInputRef.current?.click()}
        >
          <Camera className="h-4 w-4" />
          Upload
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) uploadPhoto.mutate(file);
            event.target.value = '';
          }}
        />
      </div>
      {photos.length === 0 ? (
        <p className="text-sm text-stone-500">No photos yet.</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {photos.map((photo) => (
            <div key={photo.id} className="group relative">
              <img src={thumbnailUrl(photo.id)} alt="" className="h-32 w-full rounded-lg object-cover" />
              <div className="absolute inset-0 hidden items-end justify-between rounded-lg bg-black/30 p-2 group-hover:flex">
                <button
                  type="button"
                  title={photo.id === coverPhotoId ? 'Current cover photo' : 'Set as cover photo'}
                  className="rounded bg-white/90 p-1.5 text-amber-500 hover:bg-white"
                  onClick={() => setCover.mutate(photo.id)}
                >
                  <Star className="h-4 w-4" fill={photo.id === coverPhotoId ? 'currentColor' : 'none'} />
                </button>
                <button
                  type="button"
                  title="Delete photo"
                  className="rounded bg-white/90 p-1.5 text-red-600 hover:bg-white"
                  onClick={() => deletePhoto.mutate(photo.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function CareLogTimeline({ plantId }: { plantId: string }) {
  const [eventType, setEventType] = useState('');
  const [page, setPage] = useState(0);
  const { data: logs = [] } = useLogs(plantId, eventType || undefined, page);
  const deleteLog = useDeleteLog(plantId);

  return (
    <section className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold">Care log</h2>
        <select
          className="input-base w-40"
          value={eventType}
          onChange={(event) => {
            setEventType(event.target.value);
            setPage(0);
          }}
        >
          <option value="">All events</option>
          <option value="watering">Watering</option>
          <option value="fertilising">Fertilising</option>
          <option value="repotting">Repotting</option>
        </select>
      </div>
      {logs.length === 0 ? (
        <p className="text-sm text-stone-500">No care events logged{page > 0 ? ' on this page' : ' yet'}.</p>
      ) : (
        <ul className="divide-y divide-stone-100">
          {logs.map((log) => (
            <li key={log.id} className="flex items-center justify-between py-2">
              <div>
                <span className="font-medium capitalize">{log.event_type}</span>
                <span className="ml-3 text-sm text-stone-500">{formatDateTime(log.logged_at)}</span>
                {log.notes && <p className="text-sm text-stone-500">{log.notes}</p>}
              </div>
              <button
                type="button"
                title="Delete log entry"
                className="text-stone-400 hover:text-red-600"
                onClick={() => deleteLog.mutate(log.id)}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3 flex gap-2">
        <button type="button" className="btn-secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
          Previous
        </button>
        <button
          type="button"
          className="btn-secondary"
          disabled={logs.length < LOGS_PAGE_SIZE}
          onClick={() => setPage(page + 1)}
        >
          Next
        </button>
      </div>
    </section>
  );
}

function RemindersSection({ plantId }: { plantId: string }) {
  const { data: reminders = [] } = useReminders(plantId);
  const createReminder = useCreateReminder(plantId);
  const updateReminder = useUpdateReminder(plantId);
  const deleteReminder = useDeleteReminder(plantId);
  const [eventType, setEventType] = useState('watering');
  const [intervalDays, setIntervalDays] = useState(7);

  return (
    <section className="card p-5">
      <h2 className="mb-3 font-semibold">Reminders</h2>
      {reminders.length === 0 ? (
        <p className="mb-3 text-sm text-stone-500">No reminders configured.</p>
      ) : (
        <ul className="mb-4 divide-y divide-stone-100">
          {reminders.map((reminder) => (
            <li key={reminder.id} className="flex items-center justify-between py-2">
              <div>
                <span className="font-medium capitalize">{reminder.event_type}</span>
                <span className="ml-2 text-sm text-stone-500">every {reminder.interval_days} days</span>
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1 text-sm text-stone-500">
                  <input
                    type="checkbox"
                    checked={reminder.enabled}
                    onChange={(event) =>
                      updateReminder.mutate({ id: reminder.id, enabled: event.target.checked })
                    }
                  />
                  enabled
                </label>
                <button
                  type="button"
                  title="Delete reminder"
                  className="text-stone-400 hover:text-red-600"
                  onClick={() => deleteReminder.mutate(reminder.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          createReminder.mutate({ event_type: eventType, interval_days: intervalDays, enabled: true });
        }}
      >
        <div>
          <label className="mb-1 block text-xs text-stone-500">Event</label>
          <input className="input-base w-36" value={eventType} onChange={(e) => setEventType(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-stone-500">Every (days)</label>
          <input
            type="number"
            min={1}
            className="input-base w-28"
            value={intervalDays}
            onChange={(e) => setIntervalDays(Number(e.target.value))}
          />
        </div>
        <button type="submit" className="btn-primary" disabled={createReminder.isPending}>
          <Plus className="h-4 w-4" />
          Add
        </button>
      </form>
    </section>
  );
}

export function PlantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const plantId = id ?? '';
  const navigate = useNavigate();
  const { notify } = useToast();
  const { data: plant, isLoading } = usePlant(plantId);
  const { data: locations = [] } = useLocations();
  const updatePlant = useUpdatePlant(plantId);
  const deletePlant = useDeletePlant();
  const createLog = useCreateLog(plantId);
  const [editOpen, setEditOpen] = useState(false);
  const [customLogOpen, setCustomLogOpen] = useState(false);
  const [customType, setCustomType] = useState('');
  const [customNotes, setCustomNotes] = useState('');

  if (isLoading || !plant) {
    return <p className="text-stone-500">Loading plant…</p>;
  }

  const locationName = locations.find((location) => location.id === plant.location_id)?.name;

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
              {plant.scientific_name && <p className="italic text-stone-500">{plant.scientific_name}</p>}
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
            <CareSummary plant={plant} />
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            {QUICK_ACTIONS.map(({ eventType, label, icon: Icon }) => (
              <button
                key={eventType}
                type="button"
                className="btn-primary"
                disabled={createLog.isPending}
                onClick={() =>
                  createLog.mutate({ event_type: eventType }, { onSuccess: () => notify(`${label} logged`) })
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
            <button type="button" className="btn-secondary" onClick={() => setCustomLogOpen(true)}>
              <Plus className="h-4 w-4" />
              Custom
            </button>
          </div>
        </div>
      </div>

      <PhotoGallery plantId={plant.id} coverPhotoId={plant.cover_photo_id} />
      <CareLogTimeline plantId={plant.id} />
      <RemindersSection plantId={plant.id} />

      <Modal title={`Edit ${plant.name}`} open={editOpen} onClose={() => setEditOpen(false)}>
        <PlantForm
          initial={plant}
          submitLabel="Save changes"
          busy={updatePlant.isPending}
          onSubmit={(payload) => {
            updatePlant.mutate(payload, { onSuccess: () => setEditOpen(false) });
          }}
        />
      </Modal>

      <Modal title="Log custom care event" open={customLogOpen} onClose={() => setCustomLogOpen(false)}>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (!customType.trim()) return;
            createLog.mutate(
              { event_type: customType.trim(), notes: customNotes || null },
              {
                onSuccess: () => {
                  notify(`${customType} logged`);
                  setCustomLogOpen(false);
                  setCustomType('');
                  setCustomNotes('');
                },
              },
            );
          }}
        >
          <div>
            <label className="mb-1 block text-sm font-medium">Event type</label>
            <input
              className="input-base"
              placeholder="misting, pruning, …"
              value={customType}
              onChange={(e) => setCustomType(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Notes (optional)</label>
            <textarea className="input-base" rows={2} value={customNotes} onChange={(e) => setCustomNotes(e.target.value)} />
          </div>
          <button type="submit" className="btn-primary self-start" disabled={createLog.isPending}>
            Log event
          </button>
        </form>
      </Modal>
    </div>
  );
}
