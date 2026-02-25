"use client";

import * as React from "react";
import { X, Trash2, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { ConditionBadge } from "./condition-badge";
import {
  useToothDetail,
  useOdontogramHistory,
  useRemoveCondition,
} from "@/lib/hooks/use-odontogram";
import {
  isAnteriorTooth,
  ZONE_LABELS,
  CONDITION_COLORS,
  CONDITION_LABELS,
} from "@/lib/validations/odontogram";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ToothDetailPanelProps {
  /** Patient UUID */
  patientId: string;
  /** FDI tooth number to show details for */
  toothNumber: number;
  /** Callback to close the panel */
  onClose: () => void;
  /** Callback to open full history for this tooth */
  onOpenHistory?: (toothNumber: number) => void;
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-lg" />
        <div className="space-y-1.5">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-3 w-32" />
        </div>
      </div>
      <Skeleton className="h-px w-full" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Detail panel showing all conditions and recent history for a single selected tooth.
 * Allows removing individual conditions and navigating to the full history view.
 */
function ToothDetailPanel({
  patientId,
  toothNumber,
  onClose,
  onOpenHistory,
}: ToothDetailPanelProps) {
  const { data: tooth, isLoading: isLoadingTooth } = useToothDetail(
    patientId,
    toothNumber,
  );

  const { data: history, isLoading: isLoadingHistory } = useOdontogramHistory(
    patientId,
    { tooth_number: toothNumber, limit: 10 },
  );

  const { mutate: removeCondition, isPending: isRemoving } =
    useRemoveCondition();

  const isAnterior = isAnteriorTooth(toothNumber);
  const toothType = isAnterior ? "Anterior" : "Posterior";

  // Get active conditions (zones with a non-null condition)
  const activeConditions = React.useMemo(
    () => (tooth?.zones ?? []).filter((z) => z.condition !== null),
    [tooth],
  );

  function handleRemoveCondition(conditionId: string) {
    removeCondition({ patientId, conditionId });
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader className="pb-3 flex flex-row items-start justify-between">
        <div className="space-y-1">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-50 text-primary-700 text-sm font-bold dark:bg-primary-900/20 dark:text-primary-300">
              {toothNumber}
            </span>
            <span>Diente {toothNumber}</span>
          </CardTitle>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            {toothType} &mdash;{" "}
            {activeConditions.length === 0
              ? "Sin condiciones"
              : `${activeConditions.length} condicion${activeConditions.length !== 1 ? "es" : ""}`}
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={onClose}
          aria-label="Cerrar detalle"
        >
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        {isLoadingTooth ? (
          <DetailSkeleton />
        ) : (
          <>
            {/* ── Active Conditions ──────────────────────────────────── */}
            {activeConditions.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
                Este diente no tiene condiciones registradas.
              </p>
            ) : (
              <div className="space-y-2">
                <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
                  Condiciones activas
                </p>
                {activeConditions.map((zoneData) => {
                  const condition = zoneData.condition!;
                  const zoneLabel =
                    ZONE_LABELS[zoneData.zone] ?? zoneData.zone;
                  const conditionColor =
                    condition.condition_color ??
                    CONDITION_COLORS[condition.condition_code as keyof typeof CONDITION_COLORS] ??
                    "#94A3B8";
                  const conditionLabel =
                    condition.condition_name ??
                    CONDITION_LABELS[condition.condition_code as keyof typeof CONDITION_LABELS] ??
                    condition.condition_code;

                  return (
                    <div
                      key={`${zoneData.zone}-${condition.id}`}
                      className="flex items-center justify-between rounded-md border border-[hsl(var(--border))] px-3 py-2"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <ConditionBadge
                          code={condition.condition_code}
                          label={conditionLabel}
                          colorHex={conditionColor}
                          size="sm"
                        />
                        <span className="text-[10px] text-[hsl(var(--muted-foreground))]">
                          {zoneLabel}
                        </span>
                        {condition.severity && (
                          <span className="text-[10px] text-[hsl(var(--muted-foreground))]">
                            ({condition.severity})
                          </span>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 shrink-0 text-destructive-600 hover:text-destructive-700 hover:bg-destructive-50"
                        onClick={() => handleRemoveCondition(condition.id)}
                        disabled={isRemoving}
                        aria-label={`Eliminar ${conditionLabel} de ${zoneLabel}`}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}

            <Separator />

            {/* ── Recent History ──────────────────────────────────────── */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
                  Historial reciente
                </p>
                {onOpenHistory && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-[10px] px-2"
                    onClick={() => onOpenHistory(toothNumber)}
                  >
                    <Clock className="h-3 w-3 mr-1" />
                    Ver todo
                  </Button>
                )}
              </div>

              {isLoadingHistory ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-6 w-full" />
                  ))}
                </div>
              ) : !history?.items || history.items.length === 0 ? (
                <p className="text-xs text-[hsl(var(--muted-foreground))] text-center py-2">
                  Sin historial
                </p>
              ) : (
                <div className="space-y-1.5">
                  {history.items.slice(0, 10).map((entry) => {
                    const conditionLabel =
                      CONDITION_LABELS[entry.condition_code as keyof typeof CONDITION_LABELS] ??
                      entry.condition_code;
                    const zoneLabel =
                      ZONE_LABELS[entry.zone] ?? entry.zone;

                    return (
                      <div
                        key={entry.id}
                        className="flex items-center gap-2 text-[10px] text-[hsl(var(--muted-foreground))]"
                      >
                        <span
                          className={cn(
                            "shrink-0 font-medium",
                            entry.action === "add" && "text-success-600",
                            entry.action === "remove" && "text-destructive-600",
                            entry.action === "update" && "text-primary-600",
                          )}
                        >
                          {entry.action === "add"
                            ? "+"
                            : entry.action === "remove"
                              ? "-"
                              : "~"}
                        </span>
                        <span className="truncate">
                          {conditionLabel} ({zoneLabel})
                        </span>
                        <span className="shrink-0 ml-auto">
                          {formatDateTime(entry.created_at)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

ToothDetailPanel.displayName = "ToothDetailPanel";

export { ToothDetailPanel };
