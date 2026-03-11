"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// ─── Config ───────────────────────────────────────────────────────────────────

const PAYMENT_VARIANTS: Record<string, string> = {
  pending:
    "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-700",
  paid:
    "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
  waived:
    "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
};

const PAYMENT_LABELS: Record<string, string> = {
  pending: "Pendiente",
  paid: "Pagado",
  waived: "Exonerado",
};

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Color-coded badge for an orthodontic visit's payment status.
 * Maps pending/paid/waived to semantic colors with Spanish labels.
 */
export function VisitPaymentBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium", PAYMENT_VARIANTS[status] ?? "")}
    >
      {PAYMENT_LABELS[status] ?? status}
    </Badge>
  );
}
