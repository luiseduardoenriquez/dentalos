"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  useVoiceClinicalNote,
  useSaveClinicalNote,
} from "@/lib/hooks/use-voice-clinical-note";

interface SOAPNoteReviewPanelProps {
  noteId: string;
}

const SECTION_LABELS: Record<string, string> = {
  subjective: "Subjetivo (S)",
  objective: "Objetivo (O)",
  assessment: "Evaluación (A)",
  plan: "Plan (P)",
};

export function SOAPNoteReviewPanel({ noteId }: SOAPNoteReviewPanelProps) {
  const { data: note, isLoading } = useVoiceClinicalNote(noteId);
  const saveMutation = useSaveClinicalNote(noteId);
  const [editedSections, setEditedSections] = useState<Record<string, string>>(
    {},
  );

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
        <div className="h-4 w-1/3 rounded bg-slate-200 dark:bg-slate-700" />
        <div className="h-20 rounded bg-slate-200 dark:bg-slate-700" />
        <div className="h-20 rounded bg-slate-200 dark:bg-slate-700" />
      </div>
    );
  }

  if (!note) return null;

  if (note.status === "processing") {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-primary-200 bg-primary-50 p-4 dark:border-primary-800 dark:bg-primary-900/20">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        <span className="text-sm text-primary-700 dark:text-primary-300">
          Estructurando nota clínica con IA... Esto puede tomar unos segundos.
        </span>
      </div>
    );
  }

  if (note.status === "failed") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
        <p className="text-sm font-medium text-red-800 dark:text-red-300">
          Error al estructurar la nota
        </p>
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">
          {note.error_message || "No se pudo completar. Intente nuevamente."}
        </p>
      </div>
    );
  }

  if (note.status === "saved") {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20">
        <p className="text-sm font-medium text-green-800 dark:text-green-300">
          Nota guardada como evolución clínica
        </p>
      </div>
    );
  }

  const soapNote = note.structured_note || {};

  const handleSave = async () => {
    try {
      const editedNote =
        Object.keys(editedSections).length > 0
          ? {
              ...soapNote,
              ...Object.fromEntries(
                Object.entries(editedSections).map(([key, content]) => [
                  key,
                  { ...((soapNote as any)[key] || {}), content },
                ]),
              ),
            }
          : undefined;

      await saveMutation.mutateAsync(editedNote);
      toast.success("Nota clínica guardada como evolución.");
    } catch {
      toast.error("Error al guardar la nota clínica.");
    }
  };

  return (
    <div className="space-y-4">
      {/* Transcription preview */}
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
          Transcripción original
        </p>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          {note.input_text}
        </p>
      </div>

      {/* SOAP Sections */}
      {(["subjective", "objective", "assessment", "plan"] as const).map(
        (key) => {
          const section = (soapNote as any)[key];
          if (!section) return null;
          const isEdited = key in editedSections;

          return (
            <div
              key={key}
              className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
            >
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {SECTION_LABELS[key]}
                </h4>
                <button
                  onClick={() => {
                    if (isEdited) {
                      setEditedSections((prev) => {
                        const next = { ...prev };
                        delete next[key];
                        return next;
                      });
                    } else {
                      setEditedSections((prev) => ({
                        ...prev,
                        [key]: section.content || "",
                      }));
                    }
                  }}
                  className="text-xs text-primary-600 hover:underline"
                >
                  {isEdited ? "Cancelar edición" : "Editar"}
                </button>
              </div>
              {isEdited ? (
                <textarea
                  value={editedSections[key]}
                  onChange={(e) =>
                    setEditedSections((prev) => ({
                      ...prev,
                      [key]: e.target.value,
                    }))
                  }
                  rows={3}
                  className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
                />
              ) : (
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  {section.content || "Sin contenido"}
                </p>
              )}
            </div>
          );
        },
      )}

      {/* Linked codes */}
      {(note.linked_teeth?.length ?? 0) > 0 && (
        <div className="flex flex-wrap gap-1">
          <span className="text-xs text-slate-500">Dientes:</span>
          {note.linked_teeth?.map((t) => (
            <span
              key={t}
              className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono dark:bg-slate-700"
            >
              #{t}
            </span>
          ))}
        </div>
      )}

      {note.linked_cie10_codes.length > 0 && (
        <div className="flex flex-wrap gap-1">
          <span className="text-xs text-slate-500">CIE-10:</span>
          {note.linked_cie10_codes.map((c, i) => (
            <span
              key={i}
              className="rounded bg-blue-50 px-1.5 py-0.5 text-xs dark:bg-blue-900/30"
            >
              {c.code}: {c.description}
            </span>
          ))}
        </div>
      )}

      {/* Save button */}
      {note.status === "completed" && (
        <button
          onClick={handleSave}
          disabled={saveMutation.isPending}
          className="w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {saveMutation.isPending
            ? "Guardando..."
            : "Guardar como evolución clínica"}
        </button>
      )}

      {/* AI Disclaimer */}
      <p className="text-xs text-slate-400 dark:text-slate-500">
        Nota estructurada por IA. Revise y edite antes de guardar.
      </p>
    </div>
  );
}
