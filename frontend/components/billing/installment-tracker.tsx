"use client";

import * as React from "react";
import { DollarSign } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { usePaymentPlan } from "@/lib/hooks/use-payments";
import type { InstallmentResponse } from "@/lib/hooks/use-payments";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

// ─── Installment Status Badge ────────────────────────────────────────────────

const INSTALLMENT_STATUS_LABELS: Record<InstallmentResponse["status"], string> = {
  pending: "Pendiente",
  paid: "Pagada",
  overdue: "Vencida",
};

const INSTALLMENT_STATUS_VARIANTS: Record<InstallmentResponse["status"], string> = {
  pending:
    "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-700",
  paid: "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
  overdue:
    "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
};

function InstallmentStatusBadge({ status }: { status: InstallmentResponse["status"] }) {
  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium", INSTALLMENT_STATUS_VARIANTS[status])}
    >
      {INSTALLMENT_STATUS_LABELS[status]}
    </Badge>
  );
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface InstallmentTrackerProps {
  patientId: string;
  invoiceId: string;
  onPayInstallment: (installment: InstallmentResponse) => void;
}

export function InstallmentTracker({
  patientId,
  invoiceId,
  onPayInstallment,
}: InstallmentTrackerProps) {
  const { data: plan, isLoading } = usePaymentPlan(patientId, invoiceId);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!plan) return null;

  const paidCount = plan.installments.filter((i) => i.status === "paid").length;
  const totalCount = plan.installments.length;
  const progressPercent = totalCount > 0 ? Math.round((paidCount / totalCount) * 100) : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">
            Plan de pagos
          </CardTitle>
          <Badge
            variant="outline"
            className={cn(
              "text-xs font-medium",
              plan.status === "completed"
                ? "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700"
                : plan.status === "cancelled"
                  ? "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]"
                  : "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
            )}
          >
            {plan.status === "active"
              ? "Activo"
              : plan.status === "completed"
                ? "Completado"
                : "Cancelado"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-[hsl(var(--muted-foreground))]">
            <span>
              {paidCount} de {totalCount} cuotas pagadas
            </span>
            <span className="tabular-nums font-medium">{progressPercent}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-[hsl(var(--muted))]">
            <div
              className="h-2 rounded-full bg-green-500 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Installments table */}
        <div className="overflow-x-auto rounded-md border border-[hsl(var(--border))]">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]">#</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead className="text-right">Monto</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="w-[100px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {plan.installments
                .sort((a, b) => a.installment_number - b.installment_number)
                .map((installment) => (
                  <TableRow key={installment.id}>
                    <TableCell className="text-sm tabular-nums">
                      {installment.installment_number}
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatDate(installment.due_date)}
                    </TableCell>
                    <TableCell className="text-right text-sm font-medium tabular-nums">
                      {formatCurrency(installment.amount, "COP")}
                    </TableCell>
                    <TableCell>
                      <InstallmentStatusBadge status={installment.status} />
                    </TableCell>
                    <TableCell>
                      {installment.status !== "paid" && plan.status === "active" && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => onPayInstallment(installment)}
                        >
                          <DollarSign className="mr-1 h-3 w-3" />
                          Pagar
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
