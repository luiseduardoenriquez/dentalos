"use client";

import { usePortalSurveys } from "@/lib/hooks/use-portal";

export default function PortalSurveys() {
  const { data, isLoading, isError, error, refetch } = usePortalSurveys();
  const surveys = data?.data ?? [];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[hsl(var(--foreground))]">Mis encuestas</h1>

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
      ) : surveys.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[hsl(var(--muted-foreground))]">No has completado encuestas aún</p>
        </div>
      ) : (
        <div className="space-y-4">
          {surveys.map((survey) => (
            <div key={survey.id} className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-5">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  {survey.nps_score !== null && (
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold ${
                      survey.nps_score >= 9 ? "bg-green-500" : survey.nps_score >= 7 ? "bg-yellow-500" : "bg-red-500"
                    }`}>
                      {survey.nps_score}
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium text-[hsl(var(--foreground))]">
                      {survey.nps_score !== null ? `NPS: ${survey.nps_score}/10` : ""}
                      {survey.csat_score !== null ? `${survey.nps_score !== null ? " · " : ""}CSAT: ${survey.csat_score}/5` : ""}
                    </p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {survey.responded_at ? new Date(survey.responded_at).toLocaleDateString("es-CO", { day: "numeric", month: "long", year: "numeric" }) : ""}
                    </p>
                  </div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-zinc-800 text-[hsl(var(--muted-foreground))]">
                  {survey.channel_sent === "whatsapp" ? "WhatsApp" : survey.channel_sent === "email" ? "Email" : survey.channel_sent}
                </span>
              </div>
              {survey.comments && (
                <p className="text-sm text-[hsl(var(--foreground))] mt-2 italic">"{survey.comments}"</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
