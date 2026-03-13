"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ChevronLeft,
  Send,
  RefreshCw,
  Calendar,
  User,
  Building2,
  Stethoscope,
  CheckCircle2,
  Clock,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import {
  useEPSClaim,
  useSubmitEPSClaim,
  useSyncEPSClaimStatus,
} from "@/lib/hooks/use-eps-claims";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[hsl(var(--muted))]">
        <Icon className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
      </div>
      <div>
        <p className="text-xs text-[hsl(var(--muted-foreground))]">{label}</p>
        <p className="text-sm font-medium text-foreground">{value ?? "—"}</p>
      </div>
    </div>
  );
}

interface TimelineItem {
  label: string;
  date: string | null;
  done: boolean;
}

function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <ol className="relative space-y-0">
      {items.map((item, idx) => (
        <li key={idx} className="flex items-start gap-3 pb-4 last:pb-0">
          {/* Connector line */}
          <div className="relative flex flex-col items-center">
            <div
              className={cn(
                "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2",
                item.done
                  ? "border-primary-600 bg-primary-600 text-white"
                  : "border-[hsl(var(--border))] bg-background text-[hsl(var(--muted-foreground))]",
              )}
            >
              {item.done ? (
                <CheckCircle2 className="h-3.5 w-3.5" />
              ) : (
                <Clock className="h-3.5 w-3.5" />
              )}
            </div>
            {idx < items.length - 1 && (
              <div
                className={cn(
                  "mt-1 w-0.5 grow",
                  item.done
                    ? "bg-primary-200 dark:bg-primary-800"
                    : "bg-[hsl(var(--border))]",
                )}
                style={{ minHeight: "1.5rem" }}
              />
            )}
          </div>
          <div className="pt-0.5">
            <p
              className={cn(
                "text-sm font-medium",
                item.done ? "text-foreground" : "text-[hsl(var(--muted-foreground))]",
              )}
            >
              {item.label}
            </p>
            {item.date && (
              <p className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums mt-0.5">
                {formatDate(item.date, {
                  dateStyle: "medium",
                  timeStyle: "short",
                } as Intl.DateTimeFormatOptions)}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Skeleton className="h-4 w-40" />
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-6 w-24 rounded-full" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
      </div>
      <Skeleton className="h-48 rounded-xl" />
    </div>
  );
}

// ─── Constants ────────────────────────────────────────────────────────────────

const CLAIM_TYPE_LABELS: Record<string, string> = {
  outpatient: "Ambulatorio",
  emergency: "Urgencias",
  hospitalization: "Hospitalización",
  dental: "Dental",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * EPS claim detail page — shows full claim information, procedures table,
 * status timeline, and action buttons (submit / sync status).
 */
export default function EPSClaimDetailPage() {
  const params = useParams();
  const claimId = params.id as string;

  const { data: claim, isLoading } = useEPSClaim(claimId);
  const { mutate: submitClaim, isPending: isSubmitting } =
    useSubmitEPSClaim(claimId);
  const { mutate: syncStatus, isPending: isSyncing } =
    useSyncEPSClaimStatus(claimId);

  if (isLoading) {
    return (
      <div className="p-6 max-w-4xl">
        <DetailSkeleton />
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="p-6">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          No se encontró la reclamación.
        </p>
      </div>
    );
  }

  // Timeline events
  const timelineItems: TimelineItem[] = [
    {
      label: "Creada como borrador",
      date: claim.created_at,
      done: true,
    },
    {
      label: "Enviada a la EPS",
      date: claim.submitted_at,
      done: Boolean(claim.submitted_at),
    },
    {
      label: "Confirmada por la EPS",
      date: claim.acknowledged_at,
      done: Boolean(claim.acknowledged_at),
    },
    {
      label: "Respuesta recibida",
      date: claim.response_at,
      done: Boolean(claim.response_at),
    },
  ];

  const isDraft = claim.status === "draft";
  const canSync =
    claim.status === "submitted" || claim.status === "acknowledged";

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link
          href="/billing/eps-claims"
          className="flex items-center gap-1 text-[hsl(var(--muted-foreground))] hover:text-foreground transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Reclamaciones EPS
        </Link>
        <span className="text-[hsl(var(--muted-foreground))]">/</span>
        <span className="text-foreground font-medium">Detalle</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-lg font-semibold text-foreground">
            {claim.eps_name}
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
            {CLAIM_TYPE_LABELS[claim.claim_type] ?? claim.claim_type}
            {claim.reference_number && (
              <> · Ref: <span className="font-mono">{claim.reference_number}</span></>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <EPSClaimStatusBadge status={claim.status} />
          {isDraft && (
            <Button
              size="sm"
              onClick={() => submitClaim()}
              disabled={isSubmitting}
            >
              <Send className="mr-1.5 h-3.5 w-3.5" />
              {isSubmitting ? "Enviando..." : "Enviar a EPS"}
            </Button>
          )}
          {canSync && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => syncStatus()}
              disabled={isSyncing}
            >
              <RefreshCw
                className={cn(
                  "mr-1.5 h-3.5 w-3.5",
                  isSyncing && "animate-spin",
                )}
              />
              {isSyncing ? "Sincronizando..." : "Sincronizar estado"}
            </Button>
          )}
        </div>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* EPS & Patient */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">Información</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow
              icon={User}
              label="Paciente (ID)"
              value={
                <span className="font-mono text-xs">{claim.patient_id}</span>
              }
            />
            <InfoRow
              icon={Building2}
              label="EPS"
              value={`${claim.eps_name} (${claim.eps_code})`}
            />
            <InfoRow
              icon={Stethoscope}
              label="Tipo"
              value={CLAIM_TYPE_LABELS[claim.claim_type] ?? claim.claim_type}
            />
            <InfoRow
              icon={Calendar}
              label="Fecha de creación"
              value={formatDate(claim.created_at)}
            />
          </CardContent>
        </Card>

        {/* Amounts */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">Montos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  Total reclamado
                </p>
                <p className="text-sm font-bold tabular-nums text-foreground">
                  {formatCurrency(claim.total_amount_cents, "COP")}
                </p>
              </div>
              <div className="flex items-center justify-between">
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  Copago
                </p>
                <p className="text-sm font-semibold tabular-nums text-foreground">
                  {formatCurrency(claim.copay_amount_cents, "COP")}
                </p>
              </div>
              <div className="border-t border-[hsl(var(--border))] pt-3 flex items-center justify-between">
                <p className="text-sm font-medium text-foreground">
                  Neto a pagar por EPS
                </p>
                <p className="text-base font-bold tabular-nums text-primary-600">
                  {formatCurrency(
                    claim.total_amount_cents - claim.copay_amount_cents,
                    "COP",
                  )}
                </p>
              </div>
            </div>

            {/* Rejection reason */}
            {claim.rejection_reason && (
              <div className="mt-4 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 p-3">
                <p className="text-xs font-semibold text-red-700 dark:text-red-300 mb-1">
                  Motivo de rechazo
                </p>
                <p className="text-sm text-red-700 dark:text-red-300">
                  {claim.rejection_reason}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Procedures table */}
      {claim.procedures && claim.procedures.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">
              Procedimientos ({claim.procedures.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <TableWrapper>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Código CUPS</TableHead>
                    <TableHead>Descripción</TableHead>
                    <TableHead className="text-right">Cant.</TableHead>
                    <TableHead className="text-right">P. Unitario</TableHead>
                    <TableHead className="text-right">Subtotal</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {claim.procedures.map((proc, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="text-sm font-mono text-[hsl(var(--muted-foreground))]">
                        {proc.cups_code || "—"}
                      </TableCell>
                      <TableCell className="text-sm text-foreground max-w-[240px]">
                        <p className="truncate">{proc.description || "—"}</p>
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums text-[hsl(var(--muted-foreground))]">
                        {proc.quantity}
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums text-[hsl(var(--muted-foreground))]">
                        {formatCurrency(proc.unit_cost_cents, "COP")}
                      </TableCell>
                      <TableCell className="text-right text-sm font-semibold tabular-nums text-foreground">
                        {formatCurrency(
                          proc.quantity * proc.unit_cost_cents,
                          "COP",
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableWrapper>
          </CardContent>
        </Card>
      )}

      {/* Timeline */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold">
            Historial de la reclamación
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Timeline items={timelineItems} />
        </CardContent>
      </Card>
    </div>
  );
}
