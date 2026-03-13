"use client";

import { useState, useEffect } from "react";
import {
  usePortalHealthHistory,
  usePortalUpdateHealthHistory,
} from "@/lib/hooks/use-portal";

function TagInput({
  label,
  values,
  onChange,
}: {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
}) {
  const [input, setInput] = useState("");

  function handleAdd() {
    const val = input.trim();
    if (val && !values.includes(val)) {
      onChange([...values, val]);
      setInput("");
    }
  }

  function handleRemove(idx: number) {
    onChange(values.filter((_, i) => i !== idx));
  }

  return (
    <div>
      <label className="block text-sm font-medium text-[hsl(var(--muted-foreground))] mb-1">
        {label}
      </label>
      <div className="flex flex-wrap gap-2 mb-2">
        {values.map((val, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-primary-100 text-primary-700 dark:bg-primary-950/30 dark:text-primary-400 text-xs"
          >
            {val}
            <button onClick={() => handleRemove(i)} className="hover:text-red-600">
              ✕
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleAdd();
            }
          }}
          placeholder={`Agregar ${label.toLowerCase()}...`}
          className="flex-1 px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm"
        />
        <button
          type="button"
          onClick={handleAdd}
          className="px-3 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700 transition-colors"
        >
          +
        </button>
      </div>
    </div>
  );
}

export default function PortalHealth() {
  const { data, isLoading, isError, error, refetch } = usePortalHealthHistory();
  const updateMutation = usePortalUpdateHealthHistory();

  const [allergies, setAllergies] = useState<string[]>([]);
  const [medications, setMedications] = useState<string[]>([]);
  const [conditions, setConditions] = useState<string[]>([]);
  const [surgeries, setSurgeries] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (data) {
      setAllergies(data.allergies || []);
      setMedications(data.medications || []);
      setConditions(data.conditions || []);
      setSurgeries(data.surgeries || []);
      setNotes(data.notes || "");
    }
  }, [data]);

  function markDirty<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setDirty(true);
    };
  }

  async function handleSave() {
    await updateMutation.mutateAsync({
      allergies,
      medications,
      conditions,
      surgeries,
      notes: notes || null,
    });
    setDirty(false);
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Mi salud</h1>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-red-600 dark:text-red-400 font-medium">Error al cargar los datos</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {error instanceof Error ? error.message : "Ocurrió un error inesperado."}
          </p>
          <button onClick={() => refetch()} className="mt-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors">
            Reintentar
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-5 space-y-5">
            <TagInput label="Alergias" values={allergies} onChange={markDirty(setAllergies)} />
            <TagInput label="Medicamentos" values={medications} onChange={markDirty(setMedications)} />
            <TagInput label="Condiciones médicas" values={conditions} onChange={markDirty(setConditions)} />
            <TagInput label="Cirugías previas" values={surgeries} onChange={markDirty(setSurgeries)} />

            <div>
              <label className="block text-sm font-medium text-[hsl(var(--muted-foreground))] mb-1">
                Notas adicionales
              </label>
              <textarea
                value={notes}
                onChange={(e) => { setNotes(e.target.value); setDirty(true); }}
                className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm resize-none"
                rows={3}
                placeholder="Información adicional sobre tu salud..."
              />
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={!dirty || updateMutation.isPending}
            className="w-full py-3 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
          >
            {updateMutation.isPending ? "Guardando..." : "Guardar cambios"}
          </button>

          {updateMutation.isSuccess && (
            <p className="text-sm text-green-600 text-center">Historia de salud actualizada.</p>
          )}
        </div>
      )}
    </div>
  );
}
