"use client";

import { usePortalFamily } from "@/lib/hooks/use-portal";

const RELATIONSHIP_LABELS: Record<string, string> = {
  parent: "Padre/Madre",
  child: "Hijo/a",
  spouse: "Cónyuge",
  sibling: "Hermano/a",
  other: "Otro",
};

export default function PortalFamily() {
  const { data, isLoading, isError, error, refetch } = usePortalFamily();

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Mi familia</h1>

      {isLoading ? (
        <div className="h-48 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
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
      ) : !data?.family ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">No perteneces a un grupo familiar</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Consulta con tu clínica para crear un grupo familiar.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-5">
            <h2 className="font-semibold text-[hsl(var(--foreground))] mb-4">{data.family.name}</h2>
            <div className="space-y-3">
              {data.family.members.map((member) => (
                <div key={member.id} className="flex items-center justify-between py-2 border-b border-[hsl(var(--border))] last:border-0">
                  <div>
                    <p className="text-sm font-medium text-[hsl(var(--foreground))]">
                      {member.first_name} {member.last_name}
                    </p>
                  </div>
                  <span className="px-2 py-0.5 text-xs rounded-full bg-primary-100 text-primary-700 dark:bg-primary-950/30 dark:text-primary-400">
                    {RELATIONSHIP_LABELS[member.relationship] || member.relationship}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {data.family.total_outstanding > 0 && (
            <div className="bg-white dark:bg-zinc-900 rounded-xl border border-orange-300 dark:border-orange-700 p-5">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">Saldo familiar pendiente</p>
              <p className="text-xl font-bold text-orange-600 dark:text-orange-400 mt-1">
                ${(data.family.total_outstanding / 100).toLocaleString("es-CO")}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
