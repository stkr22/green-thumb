import { useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { Camera } from 'lucide-react';

import { uploadPhoto } from '../api/hooks/usePhotos';
import { useCreatePlant } from '../api/hooks/usePlants';
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
                // The plant exists from here on, so always move to it: staying on
                // the form after a failed photo upload invites a duplicate submit.
                const file = fileInputRef.current?.files?.[0];
                let photoError: string | null = null;
                if (file) {
                  try {
                    await uploadPhoto(plant.id, file);
                  } catch (error) {
                    photoError = error instanceof Error ? error.message : 'upload failed';
                  }
                }
                if (photoError) notify(`${plant.name} created, but the photo was not saved: ${photoError}`, 'error');
                else notify(`${plant.name} created`);
                navigate(`/plants/${plant.id}`);
              },
            });
          }}
        />
        <div className="mt-4 border-t border-stone-100 pt-4">
          <p className="mb-1 block text-sm font-medium">Photo (optional)</p>
          <button type="button" className="btn-secondary" onClick={() => fileInputRef.current?.click()}>
            <Camera className="h-4 w-4" />
            {photoName || 'Choose photo'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            aria-label="Photo"
            className="hidden"
            onChange={(event) => setPhotoName(event.target.files?.[0]?.name ?? '')}
          />
        </div>
      </div>
    </div>
  );
}
