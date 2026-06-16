import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera } from 'lucide-react';

import { api } from '../api/client';
import { useCreatePlant } from '../api/hooks/usePlants';
import type { PhotoRead } from '../api/types';
import { PlantForm } from '../components/PlantForm';
import { useToast } from '../components/Toast';

export function PlantNewPage() {
  const navigate = useNavigate();
  const createPlant = useCreatePlant();
  const { notify } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [photoName, setPhotoName] = useState<string>('');

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-6 text-2xl font-bold">Add plant</h1>
      <div className="card p-6">
        <PlantForm
          submitLabel="Create plant"
          busy={createPlant.isPending}
          onSubmit={(payload) => {
            createPlant.mutate(payload, {
              onSuccess: async (plant) => {
                const file = fileInputRef.current?.files?.[0];
                if (file) {
                  const form = new FormData();
                  form.append('file', file);
                  await api<PhotoRead>(`/api/v1/plants/${plant.id}/photos`, { method: 'POST', body: form });
                }
                notify(`${plant.name} created`);
                navigate(`/plants/${plant.id}`);
              },
            });
          }}
        />
        <div className="mt-4 border-t border-stone-100 pt-4">
          <label className="mb-1 block text-sm font-medium">Photo (optional)</label>
          <button type="button" className="btn-secondary" onClick={() => fileInputRef.current?.click()}>
            <Camera className="h-4 w-4" />
            {photoName || 'Choose photo'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(event) => setPhotoName(event.target.files?.[0]?.name ?? '')}
          />
        </div>
      </div>
    </div>
  );
}
