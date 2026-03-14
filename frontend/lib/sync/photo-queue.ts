import { offlineDb, type QueuedPhoto } from "@/lib/db/offline-db";
import { apiClient } from "@/lib/api-client";

// ─── Queue Operations ─────────────────────────────────────────────────────────

/**
 * Queue a photo for upload when connectivity returns.
 * Stores the Blob in IDB (supports large files up to 25MB).
 */
export async function queuePhotoUpload(
  blob: Blob,
  fileName: string,
  uploadUrl: string,
  resource: string,
  resourceId: string,
): Promise<number> {
  return offlineDb.photo_queue.add({
    blob,
    file_name: fileName,
    upload_url: uploadUrl,
    resource,
    resource_id: resourceId,
    queued_at: Date.now(),
    retry_count: 0,
  }) as Promise<number>;
}

/**
 * Get all queued photos.
 */
export async function getQueuedPhotos(): Promise<QueuedPhoto[]> {
  return offlineDb.photo_queue.orderBy("queued_at").toArray();
}

/**
 * Get count of queued photos.
 */
export async function getQueuedPhotoCount(): Promise<number> {
  return offlineDb.photo_queue.count();
}

/**
 * Process all queued photos — upload them to the server.
 * Returns the number of successfully uploaded photos.
 */
export async function processPhotoQueue(): Promise<number> {
  const photos = await getQueuedPhotos();
  let uploaded = 0;

  for (const photo of photos) {
    try {
      const formData = new FormData();
      formData.append("file", photo.blob, photo.file_name);

      await apiClient.post(photo.upload_url, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60_000, // 60s for large files
      });

      await offlineDb.photo_queue.delete(photo.id!);
      uploaded++;
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status && status >= 400 && status < 500) {
        // Client error — remove from queue (bad request, won't succeed on retry)
        await offlineDb.photo_queue.delete(photo.id!);
      } else {
        // Network or server error — increment retry count
        await offlineDb.photo_queue.update(photo.id!, {
          retry_count: photo.retry_count + 1,
        });
        // Give up after 5 retries
        if (photo.retry_count >= 5) {
          await offlineDb.photo_queue.delete(photo.id!);
        }
      }
    }
  }

  return uploaded;
}

/**
 * Discard a single queued photo.
 */
export async function discardQueuedPhoto(id: number): Promise<void> {
  await offlineDb.photo_queue.delete(id);
}
