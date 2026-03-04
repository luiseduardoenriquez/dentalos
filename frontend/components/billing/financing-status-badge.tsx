"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export type FinancingStatus =
  | "requested"
  | "approved"
  | "disbursed"
  | "repaying"
  | "completed"
  | "rejected"
  | "cancelled";

// ─── Labels ───────────────────────────────────────────────────────────────────

export const FINANCING_STATUS_LABELS: Record<FinancingStatus, string> = {
  requested: "Solicitado",
  approved: "Aprobado",
  disbursed: "Desembolsado",
  repaying: "En pago",
  completed: "Completado",
  rejected: "Rechazado",
  cancelled: "Cancelado",
};

// ─── Styling ──────────────────────────────────────────────────────────────────

const FINANCING_STATUS_VARIANTS: Record<FinancingStatus, string> = {
  requested:
    "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-700",
  approved:
    "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
  disbursed:
    "bg-cyan-50 text-cyan-700 border-cyan-200 dark:bg-cyan-900/20 dark:text-cyan-300 dark:border-cyan-700",
  repaying:
    "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/20 dark:text-purple-300 dark:border-purple-700",
  completed:
    "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
  rejected:
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
  cancelled:
    "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
};

// ─── Component ────────────────────────────────────────────────────────────────

interface FinancingStatusBadgeProps {
  status: string;
  className?: string;
}

export function FinancingStatusBadge({ status, className }: FinancingStatusBadgeProps) {
  const safeStatus = (status as FinancingStatus) in FINANCING_STATUS_LABELS
    ? (status as FinancingStatus)
    : "requested";

  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium", FINANCING_STATUS_VARIANTS[safeStatus], className)}
    >
      {FINANCING_STATUS_LABELS[safeStatus]}
    </Badge>
  );
}
