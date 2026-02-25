"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import type { ConsentStatus } from "@/lib/hooks/use-consents";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ConsentStatusBadgeProps {
  status: ConsentStatus;
}

// ─── Status Config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  ConsentStatus,
  { label: string; variant: "secondary" | "warning" | "success" | "destructive" }
> = {
  draft: {
    label: "Borrador",
    variant: "secondary",
  },
  pending_signatures: {
    label: "Pendiente de firma",
    variant: "warning",
  },
  signed: {
    label: "Firmado",
    variant: "success",
  },
  voided: {
    label: "Anulado",
    variant: "destructive",
  },
};

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Displays a color-coded badge for a consent's lifecycle status.
 * Maps each status to a semantic badge variant and a Spanish label.
 */
function ConsentStatusBadge({ status }: ConsentStatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  if (!config) {
    return <Badge variant="outline">{status}</Badge>;
  }

  return <Badge variant={config.variant}>{config.label}</Badge>;
}

ConsentStatusBadge.displayName = "ConsentStatusBadge";

export { ConsentStatusBadge };
