"use client";

import * as React from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { TrendingUp } from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ExchangeRateDisplayProps {
  fromCurrency: string;
  toCurrency: string;
  rate: number;
  rateDate: string;
  className?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatRate(rate: number): string {
  // Use locale formatting for large numbers (e.g. COP rates)
  if (rate >= 1000) {
    return rate.toLocaleString("es-CO", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    });
  }
  return rate.toLocaleString("es-CO", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  });
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ExchangeRateDisplay({
  fromCurrency,
  toCurrency,
  rate,
  rateDate,
  className,
}: ExchangeRateDisplayProps) {
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={cn(
              "inline-flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]",
              "cursor-default hover:text-foreground transition-colors",
              className,
            )}
          >
            <TrendingUp className="h-3 w-3 shrink-0" />
            <span className="tabular-nums">
              1 {fromCurrency} = {formatRate(rate)} {toCurrency}
            </span>
          </span>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <p className="text-xs">
            Tasa de cambio actualizada el{" "}
            <span className="font-medium">{formatDate(rateDate)}</span>
          </p>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
            Fuente: tasa de referencia del mercado
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
