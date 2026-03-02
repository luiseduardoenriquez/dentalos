"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, RefreshCw, ShieldCheck } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

interface EPSVerification {
  id: string;
  patient_id: string;
  eps_code: string | null;
  eps_name: string | null;
  affiliation_status: "activo" | "inactivo" | "suspendido" | "retirado" | "no_afiliado";
  regime: string | null;
  copay_category: string | null;
  verification_date: string | null;
  created_at: string;
  updated_at: string;
}

interface EPSVerificationBadgeProps {
  patientId: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  activo:
    "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  inactivo:
    "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  suspendido:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
  retirado:
    "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
  no_afiliado:
    "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
};

const STATUS_LABELS: Record<string, string> = {
  activo: "Activo",
  inactivo: "Inactivo",
  suspendido: "Suspendido",
  retirado: "Retirado",
  no_afiliado: "No Afiliado",
};

const EPS_QUERY_KEY = (patientId: string) =>
  ["patients", patientId, "eps-verification"] as const;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Inline EPS affiliation badge for a patient.
 *
 * - Loads the latest verification from GET /patients/{id}/eps-verification.
 * - Expands to show full detail on click.
 * - Allows triggering a fresh verification via POST (same URL).
 */
export function EPSVerificationBadge({ patientId }: EPSVerificationBadgeProps) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = React.useState(false);

  // ─── Fetch current verification ─────────────────────────────────────────────
  const {
    data: verification,
    isLoading,
  } = useQuery({
    queryKey: EPS_QUERY_KEY(patientId),
    queryFn: () =>
      apiGet<EPSVerification>(`/patients/${patientId}/eps-verification`),
    retry: false,
    staleTime: 5 * 60_000,
  });

  // ─── Trigger new verification ────────────────────────────────────────────────
  const { mutate: triggerVerification, isPending: isVerifying } = useMutation({
    mutationFn: () =>
      apiPost<EPSVerification>(
        `/patients/${patientId}/eps-verification`,
        {},
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(EPS_QUERY_KEY(patientId), data);
      setExpanded(true);
    },
  });

  // ─── Loading ─────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
        <RefreshCw className="h-3 w-3 animate-spin" />
        Verificando EPS...
      </span>
    );
  }

  // ─── No verification yet ─────────────────────────────────────────────────────
  if (!verification) {
    return (
      <button
        onClick={() => triggerVerification()}
        disabled={isVerifying}
        className="inline-flex items-center gap-1 text-xs text-teal-600 hover:text-teal-700 hover:underline disabled:opacity-50 transition-colors"
      >
        {isVerifying ? (
          <>
            <RefreshCw className="h-3 w-3 animate-spin" />
            Verificando...
          </>
        ) : (
          <>
            <ShieldCheck className="h-3 w-3" />
            Verificar EPS
          </>
        )}
      </button>
    );
  }

  const status = verification.affiliation_status ?? "no_afiliado";
  const colorClass =
    STATUS_COLORS[status] ?? STATUS_COLORS.no_afiliado;
  const displayLabel =
    verification.eps_name ?? STATUS_LABELS[status] ?? status;

  const verificationDateLabel = (() => {
    const raw = verification.verification_date ?? verification.created_at;
    if (!raw) return "N/A";
    return new Date(raw).toLocaleDateString("es-CO", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  })();

  // ─── Render badge ────────────────────────────────────────────────────────────
  return (
    <div className="inline-block">
      {/* Badge trigger */}
      <button
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-opacity hover:opacity-80 ${colorClass}`}
      >
        {displayLabel}
        <ChevronDown
          className={`h-3 w-3 flex-shrink-0 transition-transform duration-150 ${
            expanded ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Expanded detail panel */}
      {expanded && (
        <div className="mt-2 p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-[hsl(var(--border))] text-xs space-y-1.5 min-w-[220px]">
          <Row label="EPS" value={verification.eps_name} />
          <Row label="Código EPS" value={verification.eps_code} />
          <Row label="Régimen" value={verification.regime} />
          <Row
            label="Categoría de copago"
            value={verification.copay_category}
          />
          <Row label="Verificado" value={verificationDateLabel} />

          <div className="pt-1">
            <button
              onClick={() => triggerVerification()}
              disabled={isVerifying}
              className="inline-flex items-center gap-1 text-teal-600 hover:underline disabled:opacity-50 transition-colors"
            >
              {isVerifying ? (
                <>
                  <RefreshCw className="h-3 w-3 animate-spin" />
                  Verificando...
                </>
              ) : (
                <>
                  <RefreshCw className="h-3 w-3" />
                  Re-verificar
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Small helper ─────────────────────────────────────────────────────────────

function Row({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <p>
      <span className="font-medium text-[hsl(var(--foreground))]">
        {label}:
      </span>{" "}
      <span className="text-[hsl(var(--muted-foreground))]">
        {value ?? "N/A"}
      </span>
    </p>
  );
}
