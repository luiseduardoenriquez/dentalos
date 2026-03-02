"use client";

import * as React from "react";
import { ArrowDownCircle, ArrowUpCircle, SlidersHorizontal } from "lucide-react";
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency, formatDateTime, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CashMovement {
  id: string;
  type: "income" | "expense" | "adjustment";
  amount_cents: number;
  description: string | null;
  payment_method: string | null;
  reference: string | null;
  created_by_name: string | null;
  created_at: string;
}

interface CashMovementListProps {
  movements: CashMovement[];
  loading?: boolean;
  emptyMessage?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MOVEMENT_TYPE_LABELS: Record<string, string> = {
  income: "Ingreso",
  expense: "Egreso",
  adjustment: "Ajuste",
};

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: "Efectivo",
  card: "Tarjeta",
  transfer: "Transferencia",
  nequi: "Nequi",
  daviplata: "Daviplata",
  insurance: "Aseguradora",
  other: "Otro",
};

// ─── Type Icon ─────────────────────────────────────────────────────────────────

function MovementTypeIcon({ type }: { type: string }) {
  if (type === "income") {
    return <ArrowDownCircle className="h-3.5 w-3.5 text-green-500" />;
  }
  if (type === "expense") {
    return <ArrowUpCircle className="h-3.5 w-3.5 text-red-500" />;
  }
  return <SlidersHorizontal className="h-3.5 w-3.5 text-yellow-500" />;
}

// ─── Type Badge ───────────────────────────────────────────────────────────────

function MovementTypeBadge({ type }: { type: string }) {
  const variants: Record<string, string> = {
    income:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
    expense:
      "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
    adjustment:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        variants[type] ?? "bg-slate-100 text-slate-700",
      )}
    >
      <MovementTypeIcon type={type} />
      {MOVEMENT_TYPE_LABELS[type] ?? type}
    </span>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function MovementSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableRow key={i} className="hover:bg-transparent">
          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
          <TableCell><Skeleton className="h-4 w-40" /></TableCell>
          <TableCell><Skeleton className="h-4 w-20" /></TableCell>
          <TableCell><Skeleton className="h-4 w-24 ml-auto" /></TableCell>
        </TableRow>
      ))}
    </>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function CashMovementList({
  movements,
  loading = false,
  emptyMessage = "No hay movimientos aún.",
}: CashMovementListProps) {
  return (
    <TableWrapper>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Hora</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>Descripción</TableHead>
            <TableHead>Método</TableHead>
            <TableHead className="text-right">Monto</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            <MovementSkeleton />
          ) : movements.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={5}
                className="h-24 text-center text-sm text-[hsl(var(--muted-foreground))]"
              >
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            movements.map((movement) => (
              <TableRow key={movement.id}>
                <TableCell className="text-sm tabular-nums text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                  {formatDateTime(movement.created_at)}
                </TableCell>
                <TableCell>
                  <MovementTypeBadge type={movement.type} />
                </TableCell>
                <TableCell className="max-w-[240px]">
                  <p className="text-sm text-foreground truncate">
                    {movement.description ?? "—"}
                  </p>
                  {movement.reference && (
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      Ref: {movement.reference}
                    </p>
                  )}
                </TableCell>
                <TableCell>
                  {movement.payment_method ? (
                    <Badge variant="secondary" className="text-xs">
                      {PAYMENT_METHOD_LABELS[movement.payment_method] ??
                        movement.payment_method}
                    </Badge>
                  ) : (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">—</span>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={cn(
                      "text-sm font-semibold tabular-nums",
                      movement.type === "income"
                        ? "text-green-600 dark:text-green-400"
                        : movement.type === "expense"
                        ? "text-red-600 dark:text-red-400"
                        : "text-yellow-600 dark:text-yellow-400",
                    )}
                  >
                    {movement.type === "income" ? "+" : movement.type === "expense" ? "−" : "±"}
                    {formatCurrency(movement.amount_cents, "COP")}
                  </span>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableWrapper>
  );
}
