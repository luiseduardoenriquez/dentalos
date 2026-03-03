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

export type AIConfidenceLevel = "high" | "medium" | "low";

export interface AIConfidenceBadgeProps {
  confidence: AIConfidenceLevel;
}

// ─── Config ───────────────────────────────────────────────────────────────────

const CONFIDENCE_CONFIG: Record<
  AIConfidenceLevel,
  { label: string; variant: "success" | "warning" | "destructive"; tooltip: string }
> = {
  high: {
    label: "Alta",
    variant: "success",
    tooltip: "La IA tiene alta confianza en esta sugerencia",
  },
  medium: {
    label: "Media",
    variant: "warning",
    tooltip: "La IA tiene confianza moderada — revisa el diagnóstico clínico",
  },
  low: {
    label: "Baja",
    variant: "destructive",
    tooltip: "La IA tiene baja confianza — usa tu criterio clínico",
  },
};

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * AIConfidenceBadge — Displays the confidence level of an AI treatment suggestion.
 *
 * high  → green  → "Alta"
 * medium → yellow → "Media"
 * low   → red    → "Baja"
 */
export function AIConfidenceBadge({ confidence }: AIConfidenceBadgeProps) {
  const config = CONFIDENCE_CONFIG[confidence];

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="cursor-default">
            <Badge variant={config.variant}>{config.label}</Badge>
          </span>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p className="text-xs max-w-[200px]">{config.tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
