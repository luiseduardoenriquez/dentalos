"use client";

import * as React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FamilyBillingMember {
  patient_id: string;
  patient_name: string;
  relationship: string;
  total_billed_cents: number;
  total_paid_cents: number;
  balance_cents: number;
}

export interface FamilyBillingSummaryProps {
  members: FamilyBillingMember[];
  className?: string;
}

// ─── Relationship labels ──────────────────────────────────────────────────────

const RELATIONSHIP_LABELS: Record<string, string> = {
  spouse: "Cónyuge",
  child: "Hijo/a",
  parent: "Padre/Madre",
  sibling: "Hermano/a",
  grandparent: "Abuelo/a",
  grandchild: "Nieto/a",
  head: "Titular",
  other: "Otro",
};

function getRelationshipLabel(relationship: string): string {
  return RELATIONSHIP_LABELS[relationship] ?? relationship;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function FamilyBillingSummary({
  members,
  className,
}: FamilyBillingSummaryProps) {
  // Compute totals
  const totals = React.useMemo(() => {
    return members.reduce(
      (acc, m) => ({
        total_billed_cents: acc.total_billed_cents + m.total_billed_cents,
        total_paid_cents: acc.total_paid_cents + m.total_paid_cents,
        balance_cents: acc.balance_cents + m.balance_cents,
      }),
      { total_billed_cents: 0, total_paid_cents: 0, balance_cents: 0 },
    );
  }, [members]);

  if (members.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
        No hay miembros en el grupo familiar.
      </p>
    );
  }

  return (
    <div className={cn("overflow-x-auto", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Paciente</TableHead>
            <TableHead>Parentesco</TableHead>
            <TableHead className="text-right">Total facturado</TableHead>
            <TableHead className="text-right">Total pagado</TableHead>
            <TableHead className="text-right">Saldo</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {members.map((member) => (
            <TableRow key={member.patient_id}>
              <TableCell className="font-medium text-foreground">
                {member.patient_name}
              </TableCell>

              <TableCell>
                <Badge variant="secondary" className="text-xs">
                  {getRelationshipLabel(member.relationship)}
                </Badge>
              </TableCell>

              <TableCell className="text-right tabular-nums text-sm">
                {formatCurrency(member.total_billed_cents)}
              </TableCell>

              <TableCell className="text-right tabular-nums text-sm text-green-600 dark:text-green-400">
                {formatCurrency(member.total_paid_cents)}
              </TableCell>

              <TableCell
                className={cn(
                  "text-right tabular-nums text-sm font-semibold",
                  member.balance_cents > 0
                    ? "text-red-600 dark:text-red-400"
                    : member.balance_cents === 0
                      ? "text-[hsl(var(--muted-foreground))]"
                      : "text-green-600 dark:text-green-400",
                )}
              >
                {formatCurrency(member.balance_cents)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>

        {/* ─── Footer totals ──────────────────────────────────────────────── */}
        <TableFooter>
          <TableRow className="bg-[hsl(var(--muted))]/40 font-semibold border-t-2 border-[hsl(var(--border))]">
            <TableCell
              colSpan={2}
              className="font-bold text-foreground"
            >
              Total grupo familiar
            </TableCell>

            <TableCell className="text-right tabular-nums font-bold text-foreground">
              {formatCurrency(totals.total_billed_cents)}
            </TableCell>

            <TableCell className="text-right tabular-nums font-bold text-green-700 dark:text-green-300">
              {formatCurrency(totals.total_paid_cents)}
            </TableCell>

            <TableCell
              className={cn(
                "text-right tabular-nums font-bold",
                totals.balance_cents > 0
                  ? "text-red-700 dark:text-red-300"
                  : totals.balance_cents === 0
                    ? "text-[hsl(var(--muted-foreground))]"
                    : "text-green-700 dark:text-green-300",
              )}
            >
              {formatCurrency(totals.balance_cents)}
            </TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    </div>
  );
}
