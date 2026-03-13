"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { CheckCircle2, XCircle } from "lucide-react";
import { cn, formatCurrency } from "@/lib/utils";
import type { TreatmentPlanItemResponse } from "@/lib/hooks/use-treatment-plans";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PlanItemRowProps {
  item: TreatmentPlanItemResponse;
  planStatus: string;
  onComplete?: (itemId: string) => void;
  onCancel?: (itemId: string) => void;
}

// ─── Status Badge Helpers ─────────────────────────────────────────────────────

const STATUS_LABELS: Record<TreatmentPlanItemResponse["status"], string> = {
  pending: "Pendiente",
  scheduled: "Programado",
  completed: "Completado",
  cancelled: "Cancelado",
};

function ItemStatusBadge({ status }: { status: TreatmentPlanItemResponse["status"] }) {
  const variants: Record<
    TreatmentPlanItemResponse["status"],
    { className: string }
  > = {
    pending: {
      className:
        "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-700",
    },
    scheduled: {
      className:
        "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
    },
    completed: {
      className:
        "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
    },
    cancelled: {
      className:
        "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
    },
  };

  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium", variants[status].className)}
    >
      {STATUS_LABELS[status]}
    </Badge>
  );
}

// ─── Payment Status Badge ────────────────────────────────────────────────────

const PAYMENT_STATUS_LABELS: Record<string, string> = {
  unpaid: "Sin pagar",
  invoiced: "Facturado",
  paid: "Pagado",
};

function PaymentStatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    unpaid: "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
    invoiced: "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:border-orange-700",
    paid: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-700",
  };
  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium", variants[status] ?? variants.unpaid)}
    >
      {PAYMENT_STATUS_LABELS[status] ?? "Sin pagar"}
    </Badge>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function PlanItemRow({
  item,
  planStatus,
  onComplete,
  onCancel,
}: PlanItemRowProps) {
  const isActive = planStatus === "active";
  const canAct =
    isActive && (item.status === "pending" || item.status === "scheduled");

  return (
    <TableRow
      className={cn(
        item.status === "cancelled" && "opacity-50",
      )}
    >
      {/* CUPS Code */}
      <TableCell className="font-mono text-xs text-[hsl(var(--muted-foreground))] w-[90px]">
        {item.cups_code}
      </TableCell>

      {/* Description */}
      <TableCell>
        <div className="space-y-0.5">
          <p className="text-sm font-medium text-foreground leading-snug">
            {item.cups_description}
          </p>
          {item.tooth_number && (
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Diente{" "}
              <span className="font-medium text-foreground">
                {item.tooth_number}
              </span>
            </p>
          )}
        </div>
      </TableCell>

      {/* Estimated cost */}
      <TableCell className="text-sm text-right font-medium tabular-nums w-[130px]">
        {formatCurrency(item.estimated_cost, "COP")}
      </TableCell>

      {/* Actual cost (if available) */}
      <TableCell className="text-sm text-right text-[hsl(var(--muted-foreground))] tabular-nums w-[130px]">
        {item.actual_cost !== null
          ? formatCurrency(item.actual_cost, "COP")
          : "—"}
      </TableCell>

      {/* Status */}
      <TableCell className="w-[120px]">
        <ItemStatusBadge status={item.status} />
      </TableCell>

      {/* Payment status */}
      <TableCell className="w-[110px]">
        <PaymentStatusBadge status={item.payment_status} />
      </TableCell>

      {/* Actions */}
      <TableCell className="w-[100px]">
        {canAct && (
          <div className="flex items-center gap-1">
            {onComplete && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-900/20"
                onClick={() => onComplete(item.id)}
                title="Marcar como completado"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span className="sr-only">Completar</span>
              </Button>
            )}
            {onCancel && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                onClick={() => onCancel(item.id)}
                title="Cancelar procedimiento"
              >
                <XCircle className="h-4 w-4" />
                <span className="sr-only">Cancelar</span>
              </Button>
            )}
          </div>
        )}
      </TableCell>
    </TableRow>
  );
}
