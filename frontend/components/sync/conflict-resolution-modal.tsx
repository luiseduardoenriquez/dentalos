"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ConflictItem, ResolutionChoice } from "@/lib/sync/conflict-resolution";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ConflictResolutionModalProps {
  conflicts: ConflictItem[];
  onResolve: (resolutions: Array<{ conflict: ConflictItem; choice: ResolutionChoice }>) => void;
  onDismiss: () => void;
}

const RESOURCE_LABELS: Record<string, string> = {
  patients: "Paciente",
  appointments: "Cita",
  clinical_records: "Registro clinico",
  odontogram: "Odontograma",
};

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Modal showing side-by-side comparison of local vs server data for sync conflicts.
 * User picks "Usar mi version" or "Usar version del servidor" per conflict.
 */
export function ConflictResolutionModal({
  conflicts,
  onResolve,
  onDismiss,
}: ConflictResolutionModalProps) {
  const [choices, setChoices] = useState<Map<number, ResolutionChoice>>(new Map());

  if (conflicts.length === 0) return null;

  function setChoice(index: number, choice: ResolutionChoice) {
    setChoices((prev) => {
      const next = new Map(prev);
      next.set(index, choice);
      return next;
    });
  }

  function handleResolveAll() {
    const resolutions = conflicts.map((conflict, index) => ({
      conflict,
      choice: choices.get(index) ?? ("server" as ResolutionChoice),
    }));
    onResolve(resolutions);
  }

  function handleUseAllServer() {
    const resolutions = conflicts.map((conflict) => ({
      conflict,
      choice: "server" as ResolutionChoice,
    }));
    onResolve(resolutions);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900">
        {/* Header */}
        <div className="mb-4 flex items-center gap-3">
          <AlertTriangle className="h-6 w-6 text-amber-500" />
          <div>
            <h2 className="text-lg font-semibold">
              Conflictos de sincronizacion
            </h2>
            <p className="text-sm text-muted-foreground">
              {conflicts.length === 1
                ? "Se encontro 1 conflicto entre tus cambios offline y los datos del servidor."
                : `Se encontraron ${conflicts.length} conflictos entre tus cambios offline y los datos del servidor.`}
            </p>
          </div>
        </div>

        {/* Conflicts */}
        <div className="space-y-4">
          {conflicts.map((conflict, index) => (
            <div key={index} className="rounded-lg border p-4">
              <div className="mb-2 text-sm font-medium">
                {RESOURCE_LABELS[conflict.resource] ?? conflict.resource}
                {conflict.resource_id && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({conflict.resource_id.slice(0, 8)}...)
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                {/* Local version */}
                <div
                  className={`cursor-pointer rounded-md border-2 p-3 transition-colors ${
                    choices.get(index) === "local"
                      ? "border-primary-500 bg-primary-50 dark:bg-primary-950/30"
                      : "border-transparent hover:border-slate-300 dark:hover:border-zinc-600"
                  }`}
                  onClick={() => setChoice(index, "local")}
                >
                  <div className="mb-1 text-xs font-medium text-amber-600">
                    Tu version (offline)
                  </div>
                  <pre className="max-h-24 overflow-auto text-xs text-muted-foreground">
                    {JSON.stringify(conflict.local_data, null, 2).slice(0, 200)}
                  </pre>
                </div>

                {/* Server version */}
                <div
                  className={`cursor-pointer rounded-md border-2 p-3 transition-colors ${
                    choices.get(index) === "server" || !choices.has(index)
                      ? "border-primary-500 bg-primary-50 dark:bg-primary-950/30"
                      : "border-transparent hover:border-slate-300 dark:hover:border-zinc-600"
                  }`}
                  onClick={() => setChoice(index, "server")}
                >
                  <div className="mb-1 text-xs font-medium text-emerald-600">
                    Version del servidor
                  </div>
                  <pre className="max-h-24 overflow-auto text-xs text-muted-foreground">
                    {JSON.stringify(conflict.server_data, null, 2).slice(0, 200)}
                  </pre>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="ghost" onClick={onDismiss}>
            Resolver despues
          </Button>
          <Button variant="outline" onClick={handleUseAllServer}>
            Usar todas del servidor
          </Button>
          <Button onClick={handleResolveAll}>
            Aplicar seleccion
          </Button>
        </div>
      </div>
    </div>
  );
}
