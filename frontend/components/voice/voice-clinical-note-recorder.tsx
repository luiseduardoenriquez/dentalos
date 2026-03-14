"use client";

import { toast } from "sonner";
import { useStructureClinicalNote } from "@/lib/hooks/use-voice-clinical-note";

interface VoiceClinicalNoteRecorderProps {
  sessionId: string;
  onNoteCreated?: (noteId: string) => void;
  disabled?: boolean;
}

export function VoiceClinicalNoteRecorder({
  sessionId,
  onNoteCreated,
  disabled = false,
}: VoiceClinicalNoteRecorderProps) {
  const structureMutation = useStructureClinicalNote();

  const handleStructure = async () => {
    try {
      const note = await structureMutation.mutateAsync({ sessionId });
      toast.success("Nota clínica en proceso de estructuración...");
      onNoteCreated?.(note.id);
    } catch (error: any) {
      if (error?.response?.status === 402) {
        toast.error(
          "El dictado de notas clínicas requiere el add-on AI Voice ($10/doctor/mes).",
          { duration: 5000 },
        );
      } else {
        toast.error("Error al iniciar la estructuración de la nota clínica.");
      }
    }
  };

  return (
    <button
      onClick={handleStructure}
      disabled={disabled || structureMutation.isPending}
      className="inline-flex items-center gap-1.5 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
    >
      <svg
        className="h-4 w-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      {structureMutation.isPending ? "Estructurando..." : "Estructurar nota SOAP"}
    </button>
  );
}
