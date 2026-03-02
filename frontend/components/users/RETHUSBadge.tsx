"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, RefreshCw, BadgeCheck } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RETHUSVerification {
  id: string;
  user_id: string;
  rethus_number: string | null;
  full_name: string | null;
  professional_title: string | null;
  specialties: string[] | null;
  status: "pending" | "verified" | "failed" | "expired";
  verified_at: string | null;
  expires_at: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

interface RETHUSBadgeProps {
  userId: string;
  /** Pre-populated RETHUS number (from user profile). */
  rethusNumber?: string | null;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  pending:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
  verified:
    "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  failed:
    "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  expired:
    "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  verified: "Verificado RETHUS",
  failed: "Falló Verificación",
  expired: "Expirado",
};

const RETHUS_QUERY_KEY = (userId: string) =>
  ["users", userId, "rethus-verification"] as const;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Inline RETHUS (Registro Único Nacional del Talento Humano en Salud) badge
 * for a staff user.
 *
 * - Loads current status from GET /users/{id}/rethus-verification.
 * - When no RETHUS number exists, renders an input field before triggering.
 * - Expands to show full detail on click.
 */
export function RETHUSBadge({ userId, rethusNumber }: RETHUSBadgeProps) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = React.useState(false);
  const [inputNumber, setInputNumber] = React.useState(rethusNumber ?? "");
  const [showInput, setShowInput] = React.useState(false);

  // ─── Fetch current verification ─────────────────────────────────────────────
  const { data: verification, isLoading } = useQuery({
    queryKey: RETHUS_QUERY_KEY(userId),
    queryFn: () =>
      apiGet<RETHUSVerification>(`/users/${userId}/rethus-verification`),
    retry: false,
    staleTime: 10 * 60_000,
  });

  // ─── Trigger new verification ────────────────────────────────────────────────
  const { mutate: triggerVerification, isPending: isVerifying } = useMutation({
    mutationFn: (rethus_number: string) =>
      apiPost<RETHUSVerification>(`/users/${userId}/rethus-verification`, {
        rethus_number,
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(RETHUS_QUERY_KEY(userId), data);
      setShowInput(false);
      setExpanded(true);
    },
  });

  function handleVerifyClick() {
    const hasNumber =
      verification?.rethus_number ?? inputNumber.trim();
    if (!hasNumber) {
      setShowInput(true);
      return;
    }
    triggerVerification(String(hasNumber));
  }

  function handleSubmitNumber(e: React.FormEvent) {
    e.preventDefault();
    if (!inputNumber.trim()) return;
    triggerVerification(inputNumber.trim());
  }

  // ─── Loading ─────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
        <RefreshCw className="h-3 w-3 animate-spin" />
        Cargando RETHUS...
      </span>
    );
  }

  // ─── Input to enter RETHUS number ────────────────────────────────────────────
  if (showInput) {
    return (
      <form
        onSubmit={handleSubmitNumber}
        className="inline-flex items-center gap-2"
      >
        <input
          type="text"
          value={inputNumber}
          onChange={(e) => setInputNumber(e.target.value)}
          placeholder="Número RETHUS"
          className="h-7 w-36 rounded border border-[hsl(var(--input))] bg-transparent px-2 text-xs focus:outline-none focus:ring-1 focus:ring-teal-500"
          autoFocus
        />
        <button
          type="submit"
          disabled={isVerifying || !inputNumber.trim()}
          className="text-xs text-teal-600 hover:underline disabled:opacity-50 transition-colors"
        >
          {isVerifying ? "Verificando..." : "Verificar"}
        </button>
        <button
          type="button"
          onClick={() => setShowInput(false)}
          className="text-xs text-[hsl(var(--muted-foreground))] hover:underline"
        >
          Cancelar
        </button>
      </form>
    );
  }

  // ─── No verification yet ─────────────────────────────────────────────────────
  if (!verification) {
    return (
      <button
        onClick={handleVerifyClick}
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
            <BadgeCheck className="h-3 w-3" />
            Verificar RETHUS
          </>
        )}
      </button>
    );
  }

  const status = verification.status ?? "pending";
  const colorClass = STATUS_COLORS[status] ?? STATUS_COLORS.pending;
  const displayLabel = STATUS_LABELS[status] ?? status;

  const verifiedDateLabel = (() => {
    if (!verification.verified_at) return null;
    return new Date(verification.verified_at).toLocaleDateString("es-CO", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  })();

  const expiresDateLabel = (() => {
    if (!verification.expires_at) return null;
    return new Date(verification.expires_at).toLocaleDateString("es-CO", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  })();

  // ─── Render badge ─────────────────────────────────────────────────────────────
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
        <div className="mt-2 p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-[hsl(var(--border))] text-xs space-y-1.5 min-w-[240px]">
          <Row label="Número RETHUS" value={verification.rethus_number} />
          <Row label="Nombre" value={verification.full_name} />
          <Row label="Título" value={verification.professional_title} />
          <Row
            label="Especialidades"
            value={
              verification.specialties?.join(", ") ?? null
            }
          />
          {verifiedDateLabel && (
            <Row label="Verificado el" value={verifiedDateLabel} />
          )}
          {expiresDateLabel && (
            <Row label="Expira el" value={expiresDateLabel} />
          )}
          {verification.failure_reason && (
            <p className="text-red-600 dark:text-red-400">
              Motivo: {verification.failure_reason}
            </p>
          )}

          <div className="pt-1">
            <button
              onClick={handleVerifyClick}
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
