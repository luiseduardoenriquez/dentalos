"use client";

import { usePortalLabOrders } from "@/lib/hooks/use-portal";

const STATUS_STEPS = ["pending", "sent_to_lab", "in_progress", "ready", "delivered"];
const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  sent_to_lab: "Enviado al lab",
  in_progress: "En proceso",
  ready: "Listo",
  delivered: "Entregado",
  cancelled: "Cancelado",
};

const ORDER_TYPE_LABELS: Record<string, string> = {
  crown: "Corona",
  bridge: "Puente",
  denture: "Prótesis",
  implant_abutment: "Pilar de implante",
  retainer: "Retenedor",
  other: "Otro",
};

export default function PortalLabOrders() {
  const { data, isLoading, isError, error, refetch } = usePortalLabOrders();
  const orders = data?.data ?? [];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Laboratorio</h1>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-32 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
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
      ) : orders.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">No tienes órdenes de laboratorio</p>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => {
            const currentStep = STATUS_STEPS.indexOf(order.status);
            const isCancelled = order.status === "cancelled";

            return (
              <div key={order.id} className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-5">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground))]">
                      {ORDER_TYPE_LABELS[order.order_type] || order.order_type}
                    </p>
                    {order.lab_name && (
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                        Lab: {order.lab_name}
                      </p>
                    )}
                    {order.due_date && (
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        Entrega estimada: {new Date(order.due_date).toLocaleDateString("es-CO", { day: "numeric", month: "short" })}
                      </p>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                    isCancelled
                      ? "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-400"
                      : order.status === "delivered"
                        ? "bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400"
                        : "bg-primary-100 text-primary-700 dark:bg-primary-950/30 dark:text-primary-400"
                  }`}>
                    {STATUS_LABELS[order.status] || order.status}
                  </span>
                </div>

                {/* Status timeline */}
                {!isCancelled && (
                  <div className="flex items-center gap-1">
                    {STATUS_STEPS.map((step, i) => (
                      <div key={step} className="flex items-center flex-1">
                        <div className={`w-3 h-3 rounded-full shrink-0 ${
                          i <= currentStep ? "bg-primary-600" : "bg-slate-200 dark:bg-zinc-700"
                        }`} />
                        {i < STATUS_STEPS.length - 1 && (
                          <div className={`flex-1 h-0.5 ${
                            i < currentStep ? "bg-primary-600" : "bg-slate-200 dark:bg-zinc-700"
                          }`} />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
