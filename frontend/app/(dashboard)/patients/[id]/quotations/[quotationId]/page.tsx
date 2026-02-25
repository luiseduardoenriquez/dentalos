"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ChevronRight,
  AlertCircle,
  ReceiptText,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";
import { ApprovalFlow } from "@/components/approval-flow";
import { usePatient } from "@/lib/hooks/use-patients";
import {
  useQuotation,
  useApproveQuotation,
} from "@/lib/hooks/use-quotations";
import type { QuotationResponse } from "@/lib/hooks/use-quotations";
import { formatDate, formatCurrency, cn } from "@/lib/utils";

// ─── Status Badge ─────────────────────────────────────────────────────────────

const QUOTATION_STATUS_LABELS: Record<QuotationResponse["status"], string> = {
  draft: "Borrador",
  sent: "Enviada",
  approved: "Aprobada",
  rejected: "Rechazada",
  expired: "Vencida",
};

function QuotationStatusBadge({ status }: { status: QuotationResponse["status"] }) {
  const variants: Record<QuotationResponse["status"], string> = {
    draft:
      "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
    sent: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
    approved:
      "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
    rejected:
      "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
    expired:
      "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:border-orange-700",
  };
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", variants[status])}>
      {QUOTATION_STATUS_LABELS[status]}
    </Badge>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function QuotationDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-5 w-20" />
        </div>
        <Skeleton className="h-9 w-40 rounded-md" />
      </div>
      <Skeleton className="h-48 w-full rounded-xl" />
      <Skeleton className="h-32 w-full rounded-xl" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function QuotationDetailPage() {
  const params = useParams<{ id: string; quotationId: string }>();
  const { id: patientId, quotationId } = params;

  const [showApproveDialog, setShowApproveDialog] = React.useState(false);

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: quotation, isLoading: isLoadingQuotation } = useQuotation(
    patientId,
    quotationId,
  );
  const { mutate: approveQuotation, isPending: isApproving } =
    useApproveQuotation(patientId, quotationId);

  const isLoading = isLoadingPatient || isLoadingQuotation;

  function handleApprove(signatureBase64: string) {
    approveQuotation(
      { signature_base64: signatureBase64 },
      {
        onSuccess: () => {
          setShowApproveDialog(false);
        },
      },
    );
  }

  if (isLoading) {
    return <QuotationDetailSkeleton />;
  }

  if (!patient || !quotation) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Cotización no encontrada"
        description="La cotización que buscas no existe o no tienes permiso para verla."
        action={{
          label: "Volver a cotizaciones",
          href: `/patients/${patientId}/quotations`,
        }}
      />
    );
  }

  const canApprove =
    quotation.status === "draft" || quotation.status === "sent";

  const isExpiringSoon =
    canApprove &&
    quotation.days_until_expiry !== null &&
    quotation.days_until_expiry >= 0 &&
    quotation.days_until_expiry < 7;

  return (
    <>
      <div className="space-y-6">
        {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
        <nav
          className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
          aria-label="Ruta de navegación"
        >
          <Link
            href="/patients"
            className="hover:text-foreground transition-colors"
          >
            Pacientes
          </Link>
          <ChevronRight className="h-4 w-4" />
          <Link
            href={`/patients/${patientId}`}
            className="hover:text-foreground transition-colors truncate max-w-[130px]"
          >
            {patient.full_name}
          </Link>
          <ChevronRight className="h-4 w-4" />
          <Link
            href={`/patients/${patientId}/quotations`}
            className="hover:text-foreground transition-colors"
          >
            Cotizaciones
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground font-mono font-medium">
            {quotation.quotation_number}
          </span>
        </nav>

        {/* ─── Expiry Warning ──────────────────────────────────────────────── */}
        {isExpiringSoon && (
          <div className="flex items-center gap-2 rounded-md border border-orange-300 bg-orange-50 px-4 py-2.5 text-sm text-orange-700 dark:border-orange-700 dark:bg-orange-900/20 dark:text-orange-300">
            <Clock className="h-4 w-4 shrink-0" />
            <span>
              Esta cotización vence en{" "}
              <span className="font-semibold">
                {quotation.days_until_expiry === 0
                  ? "hoy"
                  : `${quotation.days_until_expiry} día${quotation.days_until_expiry !== 1 ? "s" : ""}`}
              </span>
              . Solicita la aprobación del paciente a la brevedad.
            </span>
          </div>
        )}

        {/* ─── Header ──────────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between rounded-xl border border-[hsl(var(--border))] p-5 bg-[hsl(var(--card))]">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <ReceiptText className="h-5 w-5 text-primary-600" />
              <h1 className="text-xl font-bold text-foreground font-mono">
                {quotation.quotation_number}
              </h1>
              <QuotationStatusBadge status={quotation.status} />
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[hsl(var(--muted-foreground))]">
              <span>
                Creada el{" "}
                <span className="font-medium text-foreground">
                  {formatDate(quotation.created_at)}
                </span>
              </span>
              <span>
                Válida hasta{" "}
                <span
                  className={cn(
                    "font-medium",
                    isExpiringSoon ? "text-orange-600" : "text-foreground",
                  )}
                >
                  {formatDate(quotation.valid_until)}
                </span>
              </span>
              {quotation.treatment_plan_id && (
                <span>
                  Generada desde{" "}
                  <Link
                    href={`/patients/${patientId}/treatment-plans/${quotation.treatment_plan_id}`}
                    className="font-medium text-primary-600 hover:underline"
                  >
                    plan de tratamiento
                  </Link>
                </span>
              )}
            </div>
          </div>

          {/* Approve button */}
          {canApprove && (
            <Button size="sm" onClick={() => setShowApproveDialog(true)}>
              <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
              Aprobar cotización
            </Button>
          )}
        </div>

        {/* ─── Items Table ─────────────────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Detalle de servicios
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <TableWrapper>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Descripción</TableHead>
                    <TableHead className="text-right w-[80px]">Cant.</TableHead>
                    <TableHead className="text-right w-[140px]">
                      Precio unit.
                    </TableHead>
                    <TableHead className="text-right w-[120px]">
                      Descuento
                    </TableHead>
                    <TableHead className="text-right w-[140px]">
                      Subtotal
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {quotation.items
                    .sort((a, b) => a.sort_order - b.sort_order)
                    .map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>
                          <p className="text-sm text-foreground">
                            {item.description}
                          </p>
                        </TableCell>
                        <TableCell className="text-right text-sm tabular-nums">
                          {item.quantity}
                        </TableCell>
                        <TableCell className="text-right text-sm tabular-nums">
                          {formatCurrency(item.unit_price, "COP")}
                        </TableCell>
                        <TableCell className="text-right text-sm tabular-nums text-[hsl(var(--muted-foreground))]">
                          {item.discount > 0
                            ? `−${formatCurrency(item.discount, "COP")}`
                            : "—"}
                        </TableCell>
                        <TableCell className="text-right text-sm font-medium tabular-nums">
                          {formatCurrency(item.subtotal, "COP")}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </TableWrapper>
          </CardContent>
        </Card>

        {/* ─── Totals ──────────────────────────────────────────────────────── */}
        <Card>
          <CardContent className="pt-4">
            <div className="ml-auto max-w-xs space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-[hsl(var(--muted-foreground))]">
                  Subtotal
                </span>
                <span className="tabular-nums font-medium">
                  {formatCurrency(quotation.subtotal, "COP")}
                </span>
              </div>
              {quotation.tax > 0 && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[hsl(var(--muted-foreground))]">
                    IVA / Impuesto
                  </span>
                  <span className="tabular-nums font-medium">
                    {formatCurrency(quotation.tax, "COP")}
                  </span>
                </div>
              )}
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-base font-semibold text-foreground">
                  Total
                </span>
                <span className="text-lg font-bold text-foreground tabular-nums">
                  {formatCurrency(quotation.total, "COP")}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ─── Approval Dialog ─────────────────────────────────────────────── */}
      <ApprovalFlow
        open={showApproveDialog}
        onOpenChange={setShowApproveDialog}
        title="Aprobar cotización"
        description={`El paciente ${patient.full_name} firma para aprobar la cotización ${quotation.quotation_number} por un total de ${formatCurrency(quotation.total, "COP")}.`}
        onApprove={handleApprove}
        isLoading={isApproving}
      />
    </>
  );
}
