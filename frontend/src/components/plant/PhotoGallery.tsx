import { useRef, useState } from 'react';
import { Camera, Star, Trash2 } from 'lucide-react';

import { thumbnailUrl } from '../../api/client';
import { useDeletePhoto, usePhotos, useUploadPhoto } from '../../api/hooks/usePhotos';
import { useSetCoverPhoto } from '../../api/hooks/usePlants';
import { formatDate } from '../../lib/dates';
import { useToast } from '../Toast';

export function PhotoGallery({ plantId, coverPhotoId }: { plantId: string; coverPhotoId: string | null }) {
  const { data: photos = [] } = usePhotos(plantId);
  const uploadPhoto = useUploadPhoto(plantId);
  const deletePhoto = useDeletePhoto(plantId);
  const setCover = useSetCoverPhoto(plantId);
  const { notify } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(0);

  const uploadFiles = async (files: FileList) => {
    setUploading(files.length);
    try {
      // Sequential keeps the requests small-server friendly and the counter honest.
      // A rejected file (too large, not an image) is reported by the global
      // mutation toast and must not stop the rest of the batch.
      for (const file of Array.from(files)) {
        await uploadPhoto.mutateAsync(file).catch(() => undefined);
        setUploading((count) => count - 1);
      }
    } finally {
      setUploading(0);
    }
  };

  return (
    <section className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold">Photos</h2>
        <button
          type="button"
          className="btn-secondary"
          disabled={uploading > 0}
          onClick={() => fileInputRef.current?.click()}
        >
          <Camera className="h-4 w-4" />
          {uploading > 0 ? `Uploading ${uploading}…` : 'Upload'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          aria-label="Upload photos"
          onChange={(event) => {
            if (event.target.files?.length) void uploadFiles(event.target.files);
            event.target.value = '';
          }}
        />
      </div>
      {photos.length === 0 ? (
        <p className="text-sm text-stone-500">No photos yet.</p>
      ) : (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {photos.map((photo) => {
            const isCover = photo.id === coverPhotoId;
            return (
              <li key={photo.id} className="group relative">
                <img
                  src={thumbnailUrl(photo.id)}
                  alt={`Photo from ${formatDate(photo.uploaded_at)}`}
                  loading="lazy"
                  width={400}
                  height={128}
                  className="h-32 w-full rounded-lg object-cover"
                />
                {/* Always visible on touch screens; hover/focus-revealed on desktop. */}
                <div className="absolute inset-0 flex items-end justify-between rounded-lg bg-black/20 p-2 sm:bg-black/30 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
                  <button
                    type="button"
                    aria-pressed={isCover}
                    aria-label={isCover ? 'Current cover photo' : 'Set as cover photo'}
                    title={isCover ? 'Current cover photo' : 'Set as cover photo'}
                    className="rounded bg-white/90 p-1.5 text-amber-500 hover:bg-white"
                    onClick={() => setCover.mutate(photo.id)}
                  >
                    <Star className="h-4 w-4" fill={isCover ? 'currentColor' : 'none'} />
                  </button>
                  <button
                    type="button"
                    aria-label="Delete photo"
                    title="Delete photo"
                    className="rounded bg-white/90 p-1.5 text-red-600 hover:bg-white"
                    onClick={() => {
                      // Unlike logs/reminders, a photo can't be restored client-side.
                      if (window.confirm('Delete this photo? This cannot be undone.')) {
                        deletePhoto.mutate(photo.id, { onSuccess: () => notify('Photo deleted') });
                      }
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
