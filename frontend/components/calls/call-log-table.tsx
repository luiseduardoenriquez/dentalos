"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { cn, formatDate } from "@/lib/utils";
import type { CallLogResponse } from "@/lib/hooks/use-calls";

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<CallLogResponse["status"], string> = {
  completed: "Completada",
  missed: "Perdida",
  in_progress: "En curso",
  ringing: "Sonando",
  voicemail: "Buzón de voz",
};

const STATUS_VARIANTS: Record<CallLogResponse["status"], string> = {
  completed:
    "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
  missed:
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
  in_progress:
    "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
  ringing:
    "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-700",
  voicemail:
    "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Masks a phone number, showing only the last 4 digits.
 */
function maskPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length <= 4) return phone;
  return `***${digits.slice(-4)}`;
}

/**
 * Formats duration in seconds to mm:ss string.
 */
function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds <= 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface CallLogTableProps {
  calls: CallLogResponse[];
  isLoading: boolean;
  onRowClick?: (call: CallLogResponse) => void;
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function TableRowSkeleton() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <TableRow key={i} className="hover:bg-transparent">
          <TableCell>
            <Skeleton className="h-4 w-28" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-5 w-20 rounded-full" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-20" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-5 w-24 rounded-full" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-12" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-40" />
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * DataTable for displaying call log records.
 *
 * Columns: Fecha | Dirección | Teléfono | Estado | Duración | Notas
 */
export function CallLogTable({
  calls,
  isLoading,
  onRowClick,
}: CallLogTableProps) {
  return (
    <TableWrapper>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Fecha</TableHead>
            <TableHead>Dirección</TableHead>
            <TableHead>Teléfono</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead>Duración</TableHead>
            <TableHead>Notas</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <TableRowSkeleton />
          ) : calls.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={6}
                className="h-32 text-center text-sm text-[hsl(var(--muted-foreground))]"
              >
                No hay llamadas registradas.
              </TableCell>
            </TableRow>
          ) : (
            calls.map((call) => (
              <TableRow
                key={call.id}
                className={cn(
                  onRowClick &&
                    "cursor-pointer hover:bg-[hsl(var(--muted)/50%)] transition-colors",
                )}
                onClick={() => onRowClick?.(call)}
              >
                {/* Fecha */}
                <TableCell className="text-sm tabular-nums whitespace-nowrap text-[hsl(var(--muted-foreground))]">
                  {call.started_at
                    ? formatDate(call.started_at, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      } as Intl.DateTimeFormatOptions)
                    : formatDate(call.created_at)}
                </TableCell>

                {/* Dirección */}
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs font-medium",
                      call.direction === "inbound"
                        ? "bg-cyan-50 text-cyan-700 border-cyan-200 dark:bg-cyan-900/20 dark:text-cyan-300 dark:border-cyan-700"
                        : "bg-slate-50 text-slate-700 border-slate-200 dark:bg-slate-900/20 dark:text-slate-300 dark:border-slate-700",
                    )}
                  >
                    {call.direction === "inbound" ? "Entrante" : "Saliente"}
                  </Badge>
                </TableCell>

                {/* Teléfono */}
                <TableCell className="text-sm tabular-nums text-foreground">
                  {maskPhone(call.phone_number)}
                </TableCell>

                {/* Estado */}
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs font-medium",
                      STATUS_VARIANTS[call.status],
                    )}
                  >
                    {STATUS_LABELS[call.status]}
                  </Badge>
                </TableCell>

                {/* Duración */}
                <TableCell className="text-sm tabular-nums text-[hsl(var(--muted-foreground))]">
                  {formatDuration(call.duration_seconds)}
                </TableCell>

                {/* Notas */}
                <TableCell className="max-w-[200px]">
                  {call.notes ? (
                    <p className="text-sm text-foreground truncate">
                      {call.notes}
                    </p>
                  ) : (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">
                      —
                    </span>
                  )}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableWrapper>
  );
}
