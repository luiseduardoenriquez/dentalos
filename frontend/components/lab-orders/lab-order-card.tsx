"use client";

import * as React from "react";
import { CalendarDays, FlaskConical } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import type { LabOrderResponse } from "@/lib/hooks/use-lab-orders";

// ─── Constants ────────────────────────────────────────────────────────────────

const ORDER_TYPE_LABELS: Record<string, string> = {
  corona: "Corona",
  puente: "Puente",
  protesis: "Prótesis",
  abutment_implante: "Abutment implante",
  retenedor: "Retenedor",
  otro: "Otro",
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface LabOrderCardProps {
  order: LabOrderResponse;
  onClick: () => void;
  labName?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function LabOrderCard({ order, onClick, labName }: LabOrderCardProps) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const isOverdue =
    order.due_date != null &&
    !["delivered", "cancelled"].includes(order.status) &&
    new Date(order.due_date) < today;

  const orderTypeLabel =
    ORDER_TYPE_LABELS[order.order_type] ?? order.order_type;

  const shortPatientId = order.patient_id.slice(0, 8).toUpperCase();

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full text-left rounded-lg border bg-[hsl(var(--card))] p-3 shadow-sm",
        "cursor-pointer transition-all duration-150",
        "hover:shadow-md hover:border-primary-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
        "dark:bg-[hsl(var(--card))] dark:border-[hsl(var(--border))]",
      )}
    >
      {/* Patient ID */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <p className="text-xs font-mono font-medium text-[hsl(var(--muted-foreground))]">
          #{shortPatientId}
        </p>
      </div>

      {/* Order type */}
      <p className="text-sm font-semibold text-foreground leading-tight">
        {orderTypeLabel}
      </p>

      {/* Lab name */}
      {labName && (
        <div className="flex items-center gap-1 mt-1">
          <FlaskConical className="h-3 w-3 text-[hsl(var(--muted-foreground))] shrink-0" />
          <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">
            {labName}
          </p>
        </div>
      )}

      {/* Due date */}
      {order.due_date && (
        <div
          className={cn(
            "flex items-center gap-1 mt-2",
            isOverdue
              ? "text-red-600 dark:text-red-400"
              : "text-[hsl(var(--muted-foreground))]",
          )}
        >
          <CalendarDays className="h-3 w-3 shrink-0" />
          <p className="text-xs font-medium">
            {isOverdue ? "Vencida: " : ""}
            {formatDate(order.due_date)}
          </p>
        </div>
      )}
    </button>
  );
}
