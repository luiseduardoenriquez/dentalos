"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  useRadiographAnalysis,
  useReviewRadiograph,
} from "@/lib/hooks/use-radiograph-analysis";

interface RadiographAnalysisPanelProps {
  patientId: string;
  analysisId: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
  medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  low: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
};

const FINDING_TYPE_LABELS: Record<string, string> = {
  caries: "Caries",
  bone_loss: "Pérdida ósea",
  periapical_lesion: "Lesión periapical",
  restoration: "Restauración",
  impacted_tooth: "Diente impactado",
  root_canal: "Tratamiento de conducto",
  crown: "Corona",
  missing_tooth: "Diente ausente",
  calculus: "Cálculo",
  root_resorption: "Reabsorción radicular",
  supernumerary: "Supernumerario",
  other: "Otro",
};

export function RadiographAnalysisPanel({
  patientId,
  analysisId,
}: RadiographAnalysisPanelProps) {
  const { data: analysis, isLoading } = useRadiographAnalysis(
    patientId,
    analysisId,
  );
  const reviewMutation = useReviewRadiograph(patientId, analysisId);
  const [reviewActions, setReviewActions] = useState<
    Record<number, "accept" | "reject" | "modify">
  >({});

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
        <div className="h-4 w-1/3 rounded bg-slate-200 dark:bg-slate-700" />
        <div className="h-4 w-2/3 rounded bg-slate-200 dark:bg-slate-700" />
        <div className="h-4 w-1/2 rounded bg-slate-200 dark:bg-slate-700" />
      </div>
    );
  }

  if (!analysis) return null;

  if (analysis.status === "processing") {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-primary-200 bg-primary-50 p-4 dark:border-primary-800 dark:bg-primary-900/20">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        <span className="text-sm text-primary-700 dark:text-primary-300">
          Analizando radiografía con IA... Esto puede tomar unos segundos.
        </span>
      </div>
    );
  }

  if (analysis.status === "failed") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
        <p className="text-sm font-medium text-red-800 dark:text-red-300">
          Error en el análisis
        </p>
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">
          {analysis.error_message ||
            "No se pudo completar el análisis. Intente nuevamente."}
        </p>
      </div>
    );
  }

  const findings = analysis.findings || [];

  const handleReview = async () => {
    const items = Object.entries(reviewActions).map(([index, action]) => ({
      index: parseInt(index),
      action,
    }));

    if (items.length === 0) {
      toast.warning("Seleccione una acción para al menos un hallazgo.");
      return;
    }

    try {
      await reviewMutation.mutateAsync({ items });
      toast.success("Revisión guardada correctamente.");
    } catch {
      toast.error("Error al guardar la revisión.");
    }
  };

  const setAction = (
    index: number,
    action: "accept" | "reject" | "modify",
  ) => {
    setReviewActions((prev) => ({ ...prev, [index]: action }));
  };

  return (
    <div className="space-y-4">
      {/* Summary */}
      {analysis.summary && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
          <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100">
            Resumen
          </h4>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            {analysis.summary}
          </p>
          {analysis.recommendations && (
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              <span className="font-medium">Recomendaciones: </span>
              {analysis.recommendations}
            </p>
          )}
        </div>
      )}

      {/* Findings */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100">
          Hallazgos ({findings.length})
        </h4>
        {findings.map((finding, index) => (
          <div
            key={index}
            className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  {finding.tooth_number && (
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono font-medium text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                      #{finding.tooth_number}
                    </span>
                  )}
                  <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {FINDING_TYPE_LABELS[finding.finding_type] ||
                      finding.finding_type}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_COLORS[finding.severity] || SEVERITY_COLORS.low}`}
                  >
                    {finding.severity}
                  </span>
                  <span className="text-xs text-slate-400">
                    {Math.round(finding.confidence * 100)}%
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  {finding.description}
                </p>
                {finding.suggested_action && (
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
                    Acción sugerida: {finding.suggested_action}
                  </p>
                )}
              </div>

              {/* Review actions (only if completed, not yet reviewed) */}
              {analysis.status === "completed" && (
                <div className="flex gap-1">
                  <button
                    onClick={() => setAction(index, "accept")}
                    className={`rounded px-2 py-1 text-xs ${
                      reviewActions[index] === "accept"
                        ? "bg-green-600 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-green-100 dark:bg-slate-700 dark:text-slate-300"
                    }`}
                  >
                    Aceptar
                  </button>
                  <button
                    onClick={() => setAction(index, "reject")}
                    className={`rounded px-2 py-1 text-xs ${
                      reviewActions[index] === "reject"
                        ? "bg-red-600 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-red-100 dark:bg-slate-700 dark:text-slate-300"
                    }`}
                  >
                    Rechazar
                  </button>
                </div>
              )}

              {/* Show review result if already reviewed */}
              {finding.review_action && (
                <span
                  className={`rounded px-2 py-1 text-xs font-medium ${
                    finding.review_action === "accept"
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                  }`}
                >
                  {finding.review_action === "accept"
                    ? "Aceptado"
                    : "Rechazado"}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Review submit button */}
      {analysis.status === "completed" &&
        Object.keys(reviewActions).length > 0 && (
          <button
            onClick={handleReview}
            disabled={reviewMutation.isPending}
            className="w-full rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {reviewMutation.isPending
              ? "Guardando revisión..."
              : "Guardar revisión"}
          </button>
        )}

      {/* AI Disclaimer */}
      <p className="text-xs text-slate-400 dark:text-slate-500">
        Esta es una sugerencia de IA. El diagnóstico final es responsabilidad
        del profesional.
      </p>
    </div>
  );
}
