"use client";

import * as React from "react";
import Link from "next/link";
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
import { EPSClaimStatusBadge } from "@/components/billing/eps-claim-status-badge";
import { formatCurrency, formatDate, truncate } from "@/lib/utils";
import type { EPSClaimResponse } from "@/lib/hooks/use-eps-claims";

// ─── Constants ────────────────────────────────────────────────────────────────

const CLAIM_TYPE_LABELS: Record<EPSClaimResponse["claim_type"], string> = {
  ambulatorio: "Ambulatorio",
  urgencias: "Urgencias",
  hospitalizacion: "Hospitalización",
  dental: "Dental",
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface EPSClaimsTableProps {
  claims: EPSClaimResponse[];
  isLoading: boolean;
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
            <Skeleton className="h-4 w-32" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-5 w-24 rounded-full" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-24 ml-auto" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-5 w-20 rounded-full" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-24" />
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * DataTable for displaying EPS claims.
 *
 * Columns: Paciente | EPS | Tipo | Total | Estado | Fecha
 * Each row links to /billing/eps-claims/{id}.
 */
export function EPSClaimsTable({ claims, isLoading }: EPSClaimsTableProps) {
  return (
    <TableWrapper>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Paciente</TableHead>
            <TableHead>EPS</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead>Fecha</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <TableRowSkeleton />
          ) : claims.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={6}
                className="h-32 text-center text-sm text-[hsl(var(--muted-foreground))]"
              >
                No hay reclamaciones registradas.
              </TableCell>
            </TableRow>
          ) : (
            claims.map((claim) => (
              <TableRow key={claim.id} className="group">
                {/* Paciente */}
                <TableCell className="text-sm text-[hsl(var(--muted-foreground))] tabular-nums font-mono">
                  <Link
                    href={`/billing/eps-claims/${claim.id}`}
                    className="text-primary-600 hover:text-primary-700 hover:underline"
                  >
                    {truncate(claim.patient_id, 12)}
                  </Link>
                </TableCell>

                {/* EPS */}
                <TableCell className="text-sm font-medium text-foreground">
                  {claim.eps_name}
                </TableCell>

                {/* Tipo */}
                <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                  {CLAIM_TYPE_LABELS[claim.claim_type] ?? claim.claim_type}
                </TableCell>

                {/* Total */}
                <TableCell className="text-right text-sm font-semibold tabular-nums text-foreground">
                  {formatCurrency(claim.total_amount_cents, "COP")}
                </TableCell>

                {/* Estado */}
                <TableCell>
                  <EPSClaimStatusBadge status={claim.status} />
                </TableCell>

                {/* Fecha */}
                <TableCell className="text-sm tabular-nums whitespace-nowrap text-[hsl(var(--muted-foreground))]">
                  {formatDate(claim.created_at)}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableWrapper>
  );
}
