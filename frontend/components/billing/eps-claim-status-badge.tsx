"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type EPSClaimStatus =
  | "draft"
  | "submitted"
  | "acknowledged"
  | "paid"
  | "rejected"
  | "appealed";

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<EPSClaimStatus, string> = {
  draft: "Borrador",
  submitted: "Enviada",
  acknowledged: "Confirmada",
  paid: "Pagada",
  rejected: "Rechazada",
  appealed: "Apelada",
};

const STATUS_VARIANTS: Record<EPSClaimStatus, string> = {
  draft:
    "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
  submitted:
    "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
  acknowledged:
    "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-700",
  paid: "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
  rejected:
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
  appealed:
    "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:border-orange-700",
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface EPSClaimStatusBadgeProps {
  status: string;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Badge displaying the status of an EPS claim in Spanish with appropriate color.
 */
export function EPSClaimStatusBadge({
  status,
  className,
}: EPSClaimStatusBadgeProps) {
  const knownStatus = status as EPSClaimStatus;
  const label = STATUS_LABELS[knownStatus] ?? status;
  const variant = STATUS_VARIANTS[knownStatus] ?? STATUS_VARIANTS.draft;

  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium", variant, className)}
    >
      {label}
    </Badge>
  );
}
