"use client";

import { useState } from "react";
import {
  useClinicalSummary,
  type RiskAlert,
  type ActionSuggestion,
} from "@/lib/hooks/use-clinical-summary";

interface ClinicalSummaryPanelProps {
  patientId: string;
  appointmentId?: string | null;
}

const ALERT_SEVERITY_COLORS: Record<string, string> = {
  critical: "border-red-500 bg-red-50 dark:bg-red-900/20",
  warning: "border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20",
  info: "border-blue-500 bg-blue-50 dark:bg-blue-900/20",
};

const PRIORITY_COLORS: Record<string, string> = {
  high: "text-red-700 dark:text-red-400",
  medium: "text-yellow-700 dark:text-yellow-400",
  low: "text-green-700 dark:text-green-400",
};

function SectionHeader({
  title,
  isOpen,
  onToggle,
  badge,
}: {
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  badge?: string | number;
}) {
  return (
    <button
      onClick={onToggle}
      className="flex w-full items-center justify-between rounded-lg bg-slate-50 px-4 py-2.5 text-left transition-colors hover:bg-slate-100 dark:bg-slate-800 dark:hover:bg-slate-700"
    >
      <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
        {title}
      </span>
      <div className="flex items-center gap-2">
        {badge !== undefined && (
          <span className="rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
            {badge}
          </span>
        )}
        <svg
          className={`h-4 w-4 text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </button>
  );
}

export function ClinicalSummaryPanel({
  patientId,
  appointmentId,
}: ClinicalSummaryPanelProps) {
  const { data, isLoading, error } = useClinicalSummary(patientId, appointmentId);
  const [openSections, setOpenSections] = useState<Set<string>>(
    new Set(["risk_alerts", "active_conditions", "action_suggestions"]),
  );

  const toggleSection = (key: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-10 rounded-lg bg-slate-100 dark:bg-slate-800" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-slate-200 p-4 text-center dark:border-slate-700">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {(error as any)?.response?.status === 402
            ? "El Resumen Clínico con IA requiere el plan Pro o superior."
            : "No se pudo generar el resumen clínico."}
        </p>
      </div>
    );
  }

  const { sections } = data;

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          Resumen Clínico IA
        </h3>
        {data.cached && (
          <span className="text-xs text-slate-400">En caché</span>
        )}
      </div>

      {/* Risk Alerts (always prominent if present) */}
      {sections.risk_alerts.alerts.length > 0 && (
        <div className="space-y-2">
          {sections.risk_alerts.alerts.map((alert: RiskAlert, i: number) => (
            <div
              key={i}
              className={`rounded-lg border-l-4 p-3 ${ALERT_SEVERITY_COLORS[alert.severity] || ALERT_SEVERITY_COLORS.info}`}
            >
              <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                {alert.message}
              </p>
              {alert.recommendation && (
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                  {alert.recommendation}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Patient Snapshot */}
      <div>
        <SectionHeader
          title={sections.patient_snapshot.title}
          isOpen={openSections.has("patient_snapshot")}
          onToggle={() => toggleSection("patient_snapshot")}
        />
        {openSections.has("patient_snapshot") && (
          <div className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400">
            {sections.patient_snapshot.content}
          </div>
        )}
      </div>

      {/* Today Context */}
      {sections.today_context.content && (
        <div>
          <SectionHeader
            title={sections.today_context.title}
            isOpen={openSections.has("today_context")}
            onToggle={() => toggleSection("today_context")}
          />
          {openSections.has("today_context") && (
            <div className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400">
              {sections.today_context.content}
            </div>
          )}
        </div>
      )}

      {/* Active Conditions */}
      <div>
        <SectionHeader
          title={sections.active_conditions.title}
          isOpen={openSections.has("active_conditions")}
          onToggle={() => toggleSection("active_conditions")}
          badge={sections.active_conditions.items.length || undefined}
        />
        {openSections.has("active_conditions") && (
          <div className="px-4 py-2 space-y-1">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {sections.active_conditions.content}
            </p>
            {sections.active_conditions.items.map((item, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-slate-500">
                {item.tooth && (
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono dark:bg-slate-700">
                    #{item.tooth}
                  </span>
                )}
                <span>{item.diagnosis}</span>
                {item.cie10_code && (
                  <span className="text-slate-400">({item.cie10_code})</span>
                )}
                {item.relevant_to_today && (
                  <span className="rounded bg-primary-100 px-1.5 py-0.5 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                    Hoy
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pending Treatments */}
      <div>
        <SectionHeader
          title={sections.pending_treatments.title}
          isOpen={openSections.has("pending_treatments")}
          onToggle={() => toggleSection("pending_treatments")}
          badge={sections.pending_treatments.items.length || undefined}
        />
        {openSections.has("pending_treatments") && (
          <div className="px-4 py-2 space-y-1">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {sections.pending_treatments.content}
            </p>
            {sections.pending_treatments.items.map((item, i) => (
              <div key={i} className="flex items-center justify-between text-xs text-slate-500">
                <div className="flex items-center gap-2">
                  {item.tooth && (
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono dark:bg-slate-700">
                      #{item.tooth}
                    </span>
                  )}
                  <span>{item.procedure}</span>
                  {item.planned_for_today && (
                    <span className="rounded bg-primary-100 px-1.5 py-0.5 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                      Hoy
                    </span>
                  )}
                </div>
                {item.estimated_cost_cents > 0 && (
                  <span className="font-medium">
                    ${(item.estimated_cost_cents / 100).toLocaleString("es-CO")}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Last Visit */}
      <div>
        <SectionHeader
          title={sections.last_visit_summary.title}
          isOpen={openSections.has("last_visit_summary")}
          onToggle={() => toggleSection("last_visit_summary")}
        />
        {openSections.has("last_visit_summary") && (
          <div className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400">
            {sections.last_visit_summary.content}
          </div>
        )}
      </div>

      {/* Financial Status */}
      <div>
        <SectionHeader
          title={sections.financial_status.title}
          isOpen={openSections.has("financial_status")}
          onToggle={() => toggleSection("financial_status")}
        />
        {openSections.has("financial_status") && (
          <div className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400">
            {sections.financial_status.content}
          </div>
        )}
      </div>

      {/* Action Suggestions */}
      <div>
        <SectionHeader
          title={sections.action_suggestions.title}
          isOpen={openSections.has("action_suggestions")}
          onToggle={() => toggleSection("action_suggestions")}
          badge={sections.action_suggestions.suggestions.length || undefined}
        />
        {openSections.has("action_suggestions") && (
          <div className="px-4 py-2 space-y-1">
            {sections.action_suggestions.suggestions.map(
              (s: ActionSuggestion, i: number) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className={`mt-0.5 font-medium ${PRIORITY_COLORS[s.priority] || ""}`}>
                    {s.priority === "high" ? "!" : s.priority === "medium" ? "·" : "○"}
                  </span>
                  <span className="text-slate-600 dark:text-slate-400">
                    {s.action}
                  </span>
                </div>
              ),
            )}
          </div>
        )}
      </div>

      {/* AI Disclaimer */}
      <p className="pt-1 text-xs text-slate-400 dark:text-slate-500">
        Resumen generado por IA. Verifique la información antes de tomar decisiones clínicas.
      </p>
    </div>
  );
}
