"use client";

import { Check, Circle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { InvoiceStatus } from "@/components/billing/invoice-status-badge";

interface StatusTimelineProps {
  status: InvoiceStatus;
}

const STEPS = [
  { key: "draft", label: "Borrador" },
  { key: "sent", label: "Enviada" },
  { key: "partial", label: "Parcial" },
  { key: "paid", label: "Pagada" },
] as const;

const STATUS_ORDER: Record<string, number> = {
  draft: 0,
  sent: 1,
  partial: 2,
  paid: 3,
};

export function StatusTimeline({ status }: StatusTimelineProps) {
  const isCancelled = status === "cancelled";
  const isOverdue = status === "overdue";
  const currentIndex = STATUS_ORDER[status] ?? (isOverdue ? 1 : 0);

  return (
    <div className="flex items-center gap-0 w-full">
      {STEPS.map((step, index) => {
        const isCompleted = !isCancelled && currentIndex > index;
        const isCurrent = !isCancelled && currentIndex === index;

        return (
          <div key={step.key} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full border-2 text-xs transition-colors",
                  isCancelled
                    ? "border-[hsl(var(--border))] bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]"
                    : isCompleted
                      ? "border-green-500 bg-green-500 text-white"
                      : isCurrent
                        ? isOverdue
                          ? "border-red-500 bg-red-50 text-red-600 dark:bg-red-900/20"
                          : "border-primary-600 bg-primary-50 text-primary-600 dark:bg-primary-900/20"
                        : "border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--muted-foreground))]",
                )}
              >
                {isCancelled ? (
                  <X className="h-3.5 w-3.5" />
                ) : isCompleted ? (
                  <Check className="h-3.5 w-3.5" />
                ) : (
                  <Circle className="h-3 w-3" />
                )}
              </div>
              <span
                className={cn(
                  "text-[10px] font-medium whitespace-nowrap",
                  isCancelled
                    ? "text-[hsl(var(--muted-foreground))] line-through"
                    : isCompleted
                      ? "text-green-600"
                      : isCurrent
                        ? isOverdue
                          ? "text-red-600"
                          : "text-primary-600"
                        : "text-[hsl(var(--muted-foreground))]",
                )}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {index < STEPS.length - 1 && (
              <div
                className={cn(
                  "flex-1 h-0.5 mx-2 mt-[-18px]",
                  isCancelled
                    ? "bg-[hsl(var(--border))]"
                    : currentIndex > index
                      ? "bg-green-500"
                      : "bg-[hsl(var(--border))]",
                )}
              />
            )}
          </div>
        );
      })}

      {/* Cancelled badge shown separately */}
      {isCancelled && (
        <div className="flex flex-col items-center gap-1 ml-4">
          <div className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-red-500 bg-red-50 text-red-600 dark:bg-red-900/20">
            <X className="h-3.5 w-3.5" />
          </div>
          <span className="text-[10px] font-medium text-red-600 whitespace-nowrap">
            Anulada
          </span>
        </div>
      )}
    </div>
  );
}
