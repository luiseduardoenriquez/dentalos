"use client";

import { usePortalTimeline } from "@/lib/hooks/use-portal";

export default function PortalTimeline() {
  const { data, isLoading, isError, error, refetch } = usePortalTimeline();
  const events = data?.events ?? [];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Mi progreso</h1>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-xl bg-slate-100 dark:bg-zinc-800 animate-pulse" />
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
      ) : events.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">No hay eventos en tu línea de tiempo</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Tu progreso aparecerá aquí a medida que avances en tu tratamiento.</p>
        </div>
      ) : (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-200 dark:bg-zinc-700" />

          <div className="space-y-6">
            {events.map((event) => (
              <div key={event.id} className="relative flex gap-4 pl-10">
                {/* Dot */}
                <div className={`absolute left-2.5 top-1.5 w-3 h-3 rounded-full border-2 border-white dark:border-zinc-900 ${
                  event.event_type === "procedure"
                    ? "bg-primary-600"
                    : "bg-blue-500"
                }`} />

                <div className="flex-1 bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          event.event_type === "procedure"
                            ? "bg-primary-100 text-primary-700 dark:bg-primary-950/30 dark:text-primary-400"
                            : "bg-blue-100 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400"
                        }`}>
                          {event.event_type === "procedure" ? "Procedimiento" : "Foto"}
                        </span>
                        {event.tooth_number && (
                          <span className="text-xs text-[hsl(var(--muted-foreground))]">
                            D{event.tooth_number}
                          </span>
                        )}
                      </div>
                      <p className="text-sm font-medium text-[hsl(var(--foreground))] mt-1 truncate">
                        {event.title}
                      </p>
                      {event.treatment_plan_name && (
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">
                          {event.treatment_plan_name}
                        </p>
                      )}
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] shrink-0">
                      {new Date(event.date).toLocaleDateString("es-CO", {
                        day: "numeric",
                        month: "short",
                        year: "2-digit",
                      })}
                    </p>
                  </div>

                  {event.photo_url && (
                    <div className="mt-3">
                      <img
                        src={event.photo_url}
                        alt={event.title}
                        className="w-full h-32 object-cover rounded-lg"
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
