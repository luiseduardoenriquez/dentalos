"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface NoShowRiskBadgeProps {
  riskLevel: "low" | "medium" | "high";
  riskScore: number;
}

// ─── Config ───────────────────────────────────────────────────────────────────

const RISK_CONFIG = {
  low: {
    label: "Bajo",
    variant: "success" as const,
  },
  medium: {
    label: "Medio",
    variant: "warning" as const,
  },
  high: {
    label: "Alto",
    variant: "destructive" as const,
  },
};

// ─── Component ────────────────────────────────────────────────────────────────

export function NoShowRiskBadge({ riskLevel, riskScore }: NoShowRiskBadgeProps) {
  const config = RISK_CONFIG[riskLevel];
  const scoreFormatted = (riskScore * 100).toFixed(0);

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="cursor-default">
            <Badge variant={config.variant}>{config.label}</Badge>
          </span>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p className="text-xs">
            Riesgo de inasistencia:{" "}
            <span className="font-semibold">{scoreFormatted}%</span>
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
