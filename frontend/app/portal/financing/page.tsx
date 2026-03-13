"use client";

import { usePortalFinancing } from "@/lib/hooks/use-portal";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  requested: { label: "Solicitado", color: "bg-slate-100 text-slate-700 dark:bg-zinc-800 dark:text-zinc-400" },
  pending: { label: "Pendiente", color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/30 dark:text-yellow-400" },
  approved: { label: "Aprobado", color: "bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400" },
  disbursed: { label: "Desembolsado", color: "bg-primary-100 text-primary-700 dark:bg-primary-950/30 dark:text-primary-400" },
  rejected: { label: "Rechazado", color: "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-400" },
  cancelled: { label: "Cancelado", color: "bg-slate-100 text-slate-700 dark:bg-zinc-800 dark:text-zinc-400" },
  completed: { label: "Completado", color: "bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400" },
};

const PROVIDER_LABELS: Record<string, string> = {
  addi: "Addi",
  sistecredito: "Sistecrédito",
  mercadopago: "Mercado Pago",
};

export default function PortalFinancing() {
  const { data, isLoading, isError, error, refetch } = usePortalFinancing();
  const applications = data?.data ?? [];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Financiación</h1>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-28 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
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
      ) : applications.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">No tienes solicitudes de financiación</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Consulta con tu clínica sobre opciones de financiación.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {applications.map((app) => {
            const statusInfo = STATUS_LABELS[app.status] || { label: app.status, color: "bg-slate-100 text-slate-700" };
            return (
              <div key={app.id} className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground))]">
                      {PROVIDER_LABELS[app.provider] || app.provider}
                    </p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                      {new Date(app.created_at).toLocaleDateString("es-CO", { day: "numeric", month: "long", year: "numeric" })}
                    </p>
                  </div>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${statusInfo.color}`}>
                    {statusInfo.label}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[hsl(var(--muted-foreground))]">Monto</span>
                  <span className="font-medium text-[hsl(var(--foreground))]">
                    ${(app.amount_cents / 100).toLocaleString("es-CO")}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm mt-1">
                  <span className="text-[hsl(var(--muted-foreground))]">Cuotas</span>
                  <span className="font-medium text-[hsl(var(--foreground))]">{app.installments}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
