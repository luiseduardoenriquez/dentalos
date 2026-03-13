/**
 * IndexedDB persistence layer for voice recordings.
 *
 * Provides crash-resilient storage for audio chunks during voice-to-odontogram
 * dictation. Each chunk is written to IndexedDB on arrival (fire-and-forget),
 * surviving browser crashes, tab kills, and navigation.
 *
 * Database: "dentalos-voice", version 1
 * Object stores:
 *   - voice-chunks:     individual Blob segments keyed by recording_id:chunk_index
 *   - voice-recordings: metadata per recording (status, patient, idempotency key)
 */

import { openDB, type IDBPDatabase } from "idb";

// ─── Types ────────────────────────────────────────────────────────────────────

export type RecordingStatus =
  | "recording"
  | "stopped"
  | "uploading"
  | "uploaded"
  | "failed";

export interface VoiceRecordingMeta {
  recording_id: string;
  session_id: string | null;
  patient_id: string;
  patient_name: string;
  context: string;
  mime_type: string;
  started_at: number; // Date.now()
  elapsed_seconds: number;
  status: RecordingStatus;
  idempotency_key: string;
  error_message: string | null;
}

export interface VoiceChunkEntry {
  key: string; // `${recording_id}:${chunk_index}`
  recording_id: string;
  chunk_index: number;
  blob: Blob;
  timestamp: number;
}

// ─── Database ─────────────────────────────────────────────────────────────────

const DB_NAME = "dentalos-voice";
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase> | null = null;

export function getVoiceDB(): Promise<IDBPDatabase> {
  if (dbPromise) return dbPromise;

  dbPromise = openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // voice-chunks store
      if (!db.objectStoreNames.contains("voice-chunks")) {
        const chunkStore = db.createObjectStore("voice-chunks", {
          keyPath: "key",
        });
        chunkStore.createIndex("by_recording", "recording_id", {
          unique: false,
        });
      }

      // voice-recordings store
      if (!db.objectStoreNames.contains("voice-recordings")) {
        db.createObjectStore("voice-recordings", {
          keyPath: "recording_id",
        });
      }
    },
  });

  return dbPromise;
}

// ─── Recording Metadata ───────────────────────────────────────────────────────

export async function createRecordingEntry(
  meta: Omit<VoiceRecordingMeta, "status" | "error_message">,
): Promise<string> {
  try {
    const db = await getVoiceDB();
    const entry: VoiceRecordingMeta = {
      ...meta,
      status: "recording",
      error_message: null,
    };
    await db.put("voice-recordings", entry);
    return meta.recording_id;
  } catch (err) {
    console.warn("[voice-persistence] createRecordingEntry failed:", err);
    return meta.recording_id;
  }
}

export async function updateRecordingStatus(
  recording_id: string,
  status: RecordingStatus,
  error_message?: string,
): Promise<void> {
  try {
    const db = await getVoiceDB();
    const entry = await db.get("voice-recordings", recording_id);
    if (!entry) return;
    entry.status = status;
    if (error_message !== undefined) {
      entry.error_message = error_message;
    }
    await db.put("voice-recordings", entry);
  } catch (err) {
    console.warn("[voice-persistence] updateRecordingStatus failed:", err);
  }
}

export async function updateRecordingSessionId(
  recording_id: string,
  session_id: string,
): Promise<void> {
  try {
    const db = await getVoiceDB();
    const entry = await db.get("voice-recordings", recording_id);
    if (!entry) return;
    entry.session_id = session_id;
    await db.put("voice-recordings", entry);
  } catch (err) {
    console.warn("[voice-persistence] updateRecordingSessionId failed:", err);
  }
}

export async function updateRecordingElapsed(
  recording_id: string,
  elapsed_seconds: number,
): Promise<void> {
  try {
    const db = await getVoiceDB();
    const entry = await db.get("voice-recordings", recording_id);
    if (!entry) return;
    entry.elapsed_seconds = elapsed_seconds;
    await db.put("voice-recordings", entry);
  } catch (err) {
    // Silent — non-critical metadata update
  }
}

// ─── Chunk Persistence ────────────────────────────────────────────────────────

export async function persistChunk(
  recording_id: string,
  chunk_index: number,
  blob: Blob,
): Promise<void> {
  try {
    const db = await getVoiceDB();
    const entry: VoiceChunkEntry = {
      key: `${recording_id}:${chunk_index}`,
      recording_id,
      chunk_index,
      blob,
      timestamp: Date.now(),
    };
    await db.put("voice-chunks", entry);
  } catch (err) {
    console.warn("[voice-persistence] persistChunk failed:", err);
  }
}

// ─── Assembly ─────────────────────────────────────────────────────────────────

export async function assembleRecording(
  recording_id: string,
): Promise<Blob | null> {
  try {
    const db = await getVoiceDB();
    const tx = db.transaction("voice-chunks", "readonly");
    const index = tx.store.index("by_recording");
    const chunks = await index.getAll(recording_id);
    await tx.done;

    if (chunks.length === 0) return null;

    // Sort by chunk_index to ensure correct ordering
    chunks.sort((a, b) => a.chunk_index - b.chunk_index);

    // Get mime type from recording metadata
    const meta = await db.get("voice-recordings", recording_id);
    const mimeType = meta?.mime_type || "audio/webm";

    return new Blob(
      chunks.map((c) => c.blob),
      { type: mimeType },
    );
  } catch (err) {
    console.warn("[voice-persistence] assembleRecording failed:", err);
    return null;
  }
}

// ─── Recovery Queries ─────────────────────────────────────────────────────────

export async function getPendingRecordings(): Promise<VoiceRecordingMeta[]> {
  try {
    const db = await getVoiceDB();
    const all = await db.getAll("voice-recordings");
    return all.filter(
      (r) => r.status === "stopped" || r.status === "failed",
    );
  } catch (err) {
    console.warn("[voice-persistence] getPendingRecordings failed:", err);
    return [];
  }
}

// ─── Cleanup ──────────────────────────────────────────────────────────────────

export async function cleanupRecording(recording_id: string): Promise<void> {
  try {
    const db = await getVoiceDB();

    // Delete all chunks for this recording
    const tx = db.transaction("voice-chunks", "readwrite");
    const index = tx.store.index("by_recording");
    let cursor = await index.openCursor(recording_id);
    while (cursor) {
      await cursor.delete();
      cursor = await cursor.continue();
    }
    await tx.done;

    // Delete recording metadata
    await db.delete("voice-recordings", recording_id);
  } catch (err) {
    console.warn("[voice-persistence] cleanupRecording failed:", err);
  }
}

export async function cleanupStaleRecordings(
  maxAgeMs: number = 24 * 60 * 60 * 1000,
): Promise<number> {
  try {
    const db = await getVoiceDB();
    const all = await db.getAll("voice-recordings");
    const cutoff = Date.now() - maxAgeMs;
    let cleaned = 0;

    for (const recording of all) {
      if (recording.started_at < cutoff) {
        await cleanupRecording(recording.recording_id);
        cleaned++;
      }
    }

    if (cleaned > 0) {
      console.info(
        `[voice-persistence] Cleaned up ${cleaned} stale recording(s)`,
      );
    }

    return cleaned;
  } catch (err) {
    console.warn("[voice-persistence] cleanupStaleRecordings failed:", err);
    return 0;
  }
}
