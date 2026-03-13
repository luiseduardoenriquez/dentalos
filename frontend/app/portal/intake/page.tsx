"use client";

import { useState } from "react";
import {
  usePortalIntakeForm,
  usePortalSubmitIntake,
} from "@/lib/hooks/use-portal";

export default function PortalIntake() {
  const { data, isLoading, isError, error, refetch } = usePortalIntakeForm();
  const submitMutation = usePortalSubmitIntake();
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  function handleChange(key: string, value: string) {
    setFormValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await submitMutation.mutateAsync({ form_data: formValues });
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Formularios</h1>
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-8 text-center space-y-3">
          <div className="text-4xl">✅</div>
          <p className="font-semibold text-[hsl(var(--foreground))]">Formulario enviado</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Gracias por completar tu formulario de ingreso.</p>
          <button onClick={() => { setSubmitted(false); setFormValues({}); }} className="mt-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors">
            Completar otro
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Formularios</h1>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-32 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-12 space-y-3">
          <p className="text-red-600 dark:text-red-400 font-medium">Error al cargar el formulario</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {error instanceof Error ? error.message : "Ocurrió un error inesperado."}
          </p>
          <button onClick={() => refetch()} className="mt-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors">
            Reintentar
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {data?.form_config.sections.map((section) => (
            <div key={section.key} className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-5">
              <h2 className="text-sm font-semibold text-[hsl(var(--foreground))] mb-4">{section.title}</h2>
              <div className="space-y-4">
                {section.fields.map((field) => (
                  <div key={field.key}>
                    <label className="block text-sm font-medium text-[hsl(var(--muted-foreground))] mb-1">
                      {field.label}
                    </label>
                    {field.type === "textarea" ? (
                      <textarea
                        value={formValues[field.key] || ""}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm resize-none"
                        rows={3}
                      />
                    ) : (
                      <input
                        type="text"
                        value={formValues[field.key] || ""}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          <button
            type="submit"
            disabled={submitMutation.isPending}
            className="w-full py-3 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
          >
            {submitMutation.isPending ? "Enviando..." : "Enviar formulario"}
          </button>
        </form>
      )}
    </div>
  );
}
