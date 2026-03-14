"use client";

import { useState } from "react";
import { useRadiographAnalyses } from "@/lib/hooks/use-radiograph-analysis";
import { RadiographAnalysisPanel } from "./radiograph-analysis-panel";

interface RadiographAnalysisHistoryProps {
  patientId: string;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  processing: {
    label: "Procesando",
    color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  },
  completed: {
    label: "Completado",
    color:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  },
  reviewed: {
    label: "Revisado",
    color:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  },
  failed: {
    label: "Fallido",
    color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  },
};

const TYPE_LABELS: Record<string, string> = {
  periapical: "Periapical",
  bitewing: "Bitewing",
  panoramic: "Panorámica",
  cephalometric: "Cefalométrica",
  occlusal: "Oclusal",
};

export function RadiographAnalysisHistory({
  patientId,
}: RadiographAnalysisHistoryProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const { data, isLoading } = useRadiographAnalyses(patientId, page);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 rounded-lg bg-slate-100 dark:bg-slate-800"
          />
        ))}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center dark:border-slate-600">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No hay análisis de radiografías con IA para este paciente.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {data.items.map((analysis) => {
        const status = STATUS_LABELS[analysis.status] || STATUS_LABELS.failed;
        const isSelected = selectedId === analysis.id;
        const findingsCount = analysis.findings?.length || 0;

        return (
          <div key={analysis.id}>
            <button
              onClick={() => setSelectedId(isSelected ? null : analysis.id)}
              className="w-full rounded-lg border border-slate-200 p-3 text-left transition-colors hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {TYPE_LABELS[analysis.radiograph_type] ||
                      analysis.radiograph_type}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${status.color}`}
                  >
                    {status.label}
                  </span>
                  {findingsCount > 0 && (
                    <span className="text-xs text-slate-500">
                      {findingsCount} hallazgo{findingsCount !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>
                <span className="text-xs text-slate-400">
                  {new Date(analysis.created_at).toLocaleDateString("es-CO", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              {analysis.summary && !isSelected && (
                <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">
                  {analysis.summary}
                </p>
              )}
            </button>

            {isSelected && (
              <div className="mt-2 ml-2 border-l-2 border-primary-200 pl-4 dark:border-primary-800">
                <RadiographAnalysisPanel
                  patientId={patientId}
                  analysisId={analysis.id}
                />
              </div>
            )}
          </div>
        );
      })}

      {/* Pagination */}
      {data.total > data.page_size && (
        <div className="flex justify-center gap-2 pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded px-3 py-1 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-50 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            Anterior
          </button>
          <span className="px-3 py-1 text-sm text-slate-500">
            {page} / {Math.ceil(data.total / data.page_size)}
          </span>
          <button
            onClick={() =>
              setPage((p) =>
                Math.min(Math.ceil(data.total / data.page_size), p + 1),
              )
            }
            disabled={page >= Math.ceil(data.total / data.page_size)}
            className="rounded px-3 py-1 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-50 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  );
}
