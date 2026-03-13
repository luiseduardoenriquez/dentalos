"use client";

import { AlertTriangle, Upload, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useVoiceRecovery } from "@/lib/hooks/use-voice-recovery";

function formatTimeAgo(timestamp: number): string {
  const diffMs = Date.now() - timestamp;
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "hace menos de 1 min";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return `hace ${Math.floor(hours / 24)} d`;
}

/**
 * Warning banner shown when orphaned voice recordings are detected in IndexedDB.
 * Allows the doctor to re-upload or discard recordings that survived a crash/close.
 */
export function VoiceRecoveryBanner() {
  const { pending_recordings, is_loading, retry_upload, discard_recording } =
    useVoiceRecovery();

  if (is_loading || pending_recordings.length === 0) return null;

  return (
    <div className="border-b border-amber-300 bg-amber-50 px-4 py-3 dark:border-amber-700 dark:bg-amber-950/30">
      <div className="flex items-start gap-3">
        <AlertTriangle
          className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400"
          aria-hidden="true"
        />
        <div className="flex-1 space-y-2">
          <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
            {pending_recordings.length === 1
              ? "Hay 1 grabacion sin subir"
              : `Hay ${pending_recordings.length} grabaciones sin subir`}
          </p>

          {pending_recordings.map((rec) => (
            <div
              key={rec.recording_id}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-amber-800 dark:text-amber-300"
            >
              <span>
                {rec.patient_name
                  ? `Paciente: ${rec.patient_name}`
                  : "Paciente desconocido"}
              </span>
              <span className="text-amber-600 dark:text-amber-400">
                {formatTimeAgo(rec.started_at)}
              </span>
              {rec.elapsed_seconds > 0 && (
                <span className="text-amber-600 dark:text-amber-400">
                  {Math.floor(rec.elapsed_seconds / 60)}:{String(rec.elapsed_seconds % 60).padStart(2, "0")}
                </span>
              )}
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => retry_upload(rec)}
                  className="h-7 border-amber-400 bg-amber-100 text-amber-900 hover:bg-amber-200 dark:border-amber-600 dark:bg-amber-900/50 dark:text-amber-200 dark:hover:bg-amber-900"
                >
                  <Upload className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                  Subir ahora
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => discard_recording(rec.recording_id)}
                  className="h-7 text-amber-700 hover:bg-amber-200 hover:text-amber-900 dark:text-amber-400 dark:hover:bg-amber-900 dark:hover:text-amber-200"
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                  Descartar
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
