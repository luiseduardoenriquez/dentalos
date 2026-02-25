"use client";

import * as React from "react";
import { X, Clock, Plus, RefreshCw, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ConditionBadge } from "./condition-badge";
import { useOdontogramHistory } from "@/lib/hooks/use-odontogram";
import {
  ZONE_LABELS,
  CONDITION_COLORS,
  CONDITION_LABELS,
} from "@/lib/validations/odontogram";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface HistoryPanelProps {
  /** Patient UUID */
  patientId: string;
  /** Optional: filter history to a specific tooth */
  toothNumber?: number;
  /** Whether the panel is currently visible */
  isOpen: boolean;
  /** Callback to close the panel */
  onClose: () => void;
}

// ─── Action Badge ─────────────────────────────────────────────────────────────

const ACTION_CONFIG: Record<string, { label: string; variant: "default" | "success" | "destructive"; icon: React.ComponentType<{ className?: string }> }> = {
  add: { label: "Agregado", variant: "success", icon: Plus },
  update: { label: "Actualizado", variant: "default", icon: RefreshCw },
  remove: { label: "Eliminado", variant: "destructive", icon: Trash2 },
};

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function HistorySkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex gap-3">
          <Skeleton className="h-6 w-6 rounded-full shrink-0" />
          <div className="space-y-1.5 flex-1">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Timeline sidebar showing condition change history for a patient's odontogram.
 * Supports cursor-based pagination with a "Cargar mas" button.
 * Can be filtered to show history for a specific tooth.
 */
function HistoryPanel({
  patientId,
  toothNumber,
  isOpen,
  onClose,
}: HistoryPanelProps) {
  const [cursor, setCursor] = React.useState<string | undefined>(undefined);

  // Reset cursor when filter changes
  React.useEffect(() => {
    setCursor(undefined);
  }, [toothNumber]);

  const { data: history, isLoading } = useOdontogramHistory(patientId, {
    tooth_number: toothNumber,
    cursor,
    limit: 20,
  });

  if (!isOpen) return null;

  return (
    <Card className="w-full max-w-sm">
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
          <CardTitle className="text-sm font-semibold">
            Historial
            {toothNumber && (
              <span className="ml-1 text-[hsl(var(--muted-foreground))] font-normal">
                - Diente {toothNumber}
              </span>
            )}
          </CardTitle>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={onClose}
          aria-label="Cerrar historial"
        >
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <HistorySkeleton />
        ) : !history?.items || history.items.length === 0 ? (
          <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-8">
            No hay cambios registrados
            {toothNumber ? ` para el diente ${toothNumber}` : ""}.
          </p>
        ) : (
          <div className="space-y-0">
            {/* Timeline */}
            <div className="relative">
              {/* Vertical timeline line */}
              <div className="absolute left-3 top-2 bottom-2 w-px bg-[hsl(var(--border))]" />

              {history.items.map((entry, index) => {
                const actionConfig = ACTION_CONFIG[entry.action] ?? ACTION_CONFIG.update;
                const ActionIcon = actionConfig.icon;
                const conditionColor =
                  CONDITION_COLORS[entry.condition_code as keyof typeof CONDITION_COLORS] ?? "#94A3B8";
                const conditionLabel =
                  CONDITION_LABELS[entry.condition_code as keyof typeof CONDITION_LABELS] ?? entry.condition_code;
                const zoneLabel = ZONE_LABELS[entry.zone] ?? entry.zone;

                return (
                  <div
                    key={entry.id}
                    className={cn(
                      "relative flex gap-3 pb-4",
                      index === history.items.length - 1 && "pb-0",
                    )}
                  >
                    {/* Timeline dot */}
                    <div className="relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[hsl(var(--card))] border border-[hsl(var(--border))]">
                      <ActionIcon className="h-3 w-3 text-[hsl(var(--muted-foreground))]" />
                    </div>

                    {/* Entry content */}
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant={actionConfig.variant} className="text-[10px] px-1.5 py-0">
                          {actionConfig.label}
                        </Badge>
                        <span className="text-xs font-semibold tabular-nums">
                          #{entry.tooth_number}
                        </span>
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">
                          {zoneLabel}
                        </span>
                      </div>

                      <ConditionBadge
                        code={entry.condition_code}
                        label={conditionLabel}
                        colorHex={conditionColor}
                        size="sm"
                      />

                      <div className="flex items-center gap-2 text-[10px] text-[hsl(var(--muted-foreground))]">
                        {entry.performed_by_name && (
                          <span className="truncate max-w-[120px]">
                            {entry.performed_by_name}
                          </span>
                        )}
                        <span>{formatDateTime(entry.created_at)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Load more button */}
            {history.has_more && history.next_cursor && (
              <div className="pt-4">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => setCursor(history.next_cursor!)}
                >
                  Cargar mas
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

HistoryPanel.displayName = "HistoryPanel";

export { HistoryPanel };
