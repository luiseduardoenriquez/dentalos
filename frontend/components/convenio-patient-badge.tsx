"use client";

import * as React from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ConvenioPatientBadgeProps {
  companyName: string;
  discountType: "percentage" | "fixed";
  discountValue: number;
  className?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDiscount(type: "percentage" | "fixed", value: number): string {
  if (type === "percentage") return `-${value}%`;
  return `-$${value.toLocaleString("es-CO")}`;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ConvenioPatientBadge({
  companyName,
  discountType,
  discountValue,
  className,
}: ConvenioPatientBadgeProps) {
  const discountLabel = formatDiscount(discountType, discountValue);
  const tooltipText =
    discountType === "percentage"
      ? `${companyName} — ${discountValue}% de descuento en todos los procedimientos`
      : `${companyName} — $${discountValue.toLocaleString("es-CO")} COP de descuento fijo por procedimiento`;

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className={cn("inline-flex cursor-default", className)}>
            <Badge
              variant="default"
              className="gap-1 bg-teal-100 text-teal-700 border border-teal-200 dark:bg-teal-900/30 dark:text-teal-300 dark:border-teal-700"
            >
              <Building2 className="h-3 w-3 shrink-0" />
              Convenio: {companyName}
              <span className="font-bold text-teal-800 dark:text-teal-200 ml-0.5">
                ({discountLabel})
              </span>
            </Badge>
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <p className="text-xs max-w-[220px]">{tooltipText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
