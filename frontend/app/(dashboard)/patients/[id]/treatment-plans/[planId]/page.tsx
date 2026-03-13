"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronRight,
  AlertCircle,
  FileText,
  ReceiptText,
  XCircle,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";
import { ApprovalFlow } from "@/components/approval-flow";
import { PlanItemRow } from "@/components/plan-item-row";
import { usePatient } from "@/lib/hooks/use-patients";
import {
  useTreatmentPlan,
  useApproveTreatmentPlan,
  useCancelTreatmentPlan,
} from "@/lib/hooks/use-treatment-plans";
import type { TreatmentPlanResponse } from "@/lib/hooks/use-treatment-plans";
import { useCreateQuotation } from "@/lib/hooks/use-quotations";
import { formatDate, formatCurrency, cn } from "@/lib/utils";

// ─── Status Badge ─────────────────────────────────────────────────────────────

const PLAN_STATUS_LABELS: Record<TreatmentPlanResponse["status"], string> = {
  draft: "Borrador",
  active: "Activo",
  completed: "Completado",
  cancelled: "Cancelado",
};

function PlanStatusBadge({ status }: { status: TreatmentPlanResponse["status"] }) {
  const variants: Record<TreatmentPlanResponse["status"], string> = {
    draft: "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
    active: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-700",
    completed: "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
    cancelled: "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
  };
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", variants[status])}>
      {PLAN_STATUS_LABELS[status]}
    </Badge>
  );
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────

function ProgressBar({ value }: { value: number }) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className="flex items-center gap-3">
      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-[hsl(var(--muted))]">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            clamped === 100 ? "bg-green-500" : clamped > 50 ? "bg-blue-500" : "bg-primary-600",
          )}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="text-sm font-semibold tabular-nums text-foreground w-10 text-right">
        {clamped}%
      </span>
    </div>
  );
}

// ─── Summary Card ─────────────────────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium uppercase tracking-wide">
          {label}
        </p>
        <p className="text-xl font-bold text-foreground mt-1">{value}</p>
        {sub && (
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
            {sub}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function PlanDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-5 w-20" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-32 rounded-md" />
          <Skeleton className="h-9 w-28 rounded-md" />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-48 w-full rounded-xl" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TreatmentPlanDetailPage() {
  const params = useParams<{ id: string; planId: string }>();
  const router = useRouter();
  const { id: patientId, planId } = params;

  const [showApproveDialog, setShowApproveDialog] = React.useState(false);
  const [showCancelDialog, setShowCancelDialog] = React.useState(false);

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: plan, isLoading: isLoadingPlan } = useTreatmentPlan(patientId, planId);
  const { mutate: approvePlan, isPending: isApproving } = useApproveTreatmentPlan(patientId, planId);
  const { mutate: cancelPlan, isPending: isCancelling } = useCancelTreatmentPlan(patientId, planId);
  const { mutate: createQuotation, isPending: isCreatingQuotation } = useCreateQuotation(patientId);

  const isLoading = isLoadingPatient || isLoadingPlan;

  function handleApprove(signatureBase64: string) {
    approvePlan(
      { signature_base64: signatureBase64 },
      {
        onSuccess: () => {
          setShowApproveDialog(false);
        },
      },
    );
  }

  function handleCancel() {
    cancelPlan(undefined, {
      onSuccess: () => {
        setShowCancelDialog(false);
      },
    });
  }

  function handleGenerateQuotation() {
    createQuotation(
      { treatment_plan_id: planId },
      {
        onSuccess: (quotation) => {
          router.push(`/patients/${patientId}/quotations/${quotation.id}`);
        },
      },
    );
  }

  if (isLoading) {
    return <PlanDetailSkeleton />;
  }

  if (!patient || !plan) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Plan no encontrado"
        description="El plan de tratamiento que buscas no existe o no tienes permiso para verlo."
        action={{
          label: "Volver a planes",
          href: `/patients/${patientId}/treatment-plans`,
        }}
      />
    );
  }

  const canApprove = plan.status === "draft";
  const canCancel = plan.status === "draft" || plan.status === "active";
  const canGenerateQuotation =
    plan.status === "draft" || plan.status === "active";

  return (
    <>
      <div className="space-y-6">
        {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
        <nav
          className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
          aria-label="Ruta de navegación"
        >
          <Link href="/patients" className="hover:text-foreground transition-colors">
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
            href={`/patients/${patientId}/treatment-plans`}
            className="hover:text-foreground transition-colors"
          >
            Planes de tratamiento
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground font-medium truncate max-w-[160px]">
            {plan.name}
          </span>
        </nav>

        {/* ─── Header ──────────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between rounded-xl border border-[hsl(var(--border))] p-5 bg-[hsl(var(--card))]">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold text-foreground">{plan.name}</h1>
              <PlanStatusBadge status={plan.status} />
            </div>
            {plan.description && (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                {plan.description}
              </p>
            )}
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Creado el{" "}
              <span className="font-medium text-foreground">
                {formatDate(plan.created_at)}
              </span>
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2 sm:flex-col sm:items-end md:flex-row">
            {canApprove && (
              <Button
                size="sm"
                onClick={() => setShowApproveDialog(true)}
                disabled={isApproving || plan.items.length === 0}
              >
                <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                Aprobar plan
              </Button>
            )}
            {canGenerateQuotation && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateQuotation}
                disabled={isCreatingQuotation || plan.items.length === 0}
              >
                <ReceiptText className="mr-1.5 h-3.5 w-3.5" />
                {isCreatingQuotation ? "Generando..." : "Generar cotización"}
              </Button>
            )}
            {canCancel && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowCancelDialog(true)}
                disabled={isCancelling}
              >
                <XCircle className="mr-1.5 h-3.5 w-3.5" />
                Cancelar
              </Button>
            )}
          </div>
        </div>

        {/* ─── Progress ────────────────────────────────────────────────────── */}
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-2">
              Progreso general
            </p>
            <ProgressBar value={plan.progress_percent} />
          </CardContent>
        </Card>

        {/* ─── Summary Cards ───────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard
            label="Costo estimado"
            value={formatCurrency(plan.total_cost_estimated, "COP")}
            sub={`${plan.items.length} procedimiento${plan.items.length !== 1 ? "s" : ""}`}
          />
          <SummaryCard
            label="Costo real"
            value={
              plan.total_cost_actual > 0
                ? formatCurrency(plan.total_cost_actual, "COP")
                : "—"
            }
            sub="Procedimientos completados"
          />
          <SummaryCard
            label="Progreso"
            value={`${plan.progress_percent}%`}
            sub={`${plan.items.filter((i) => i.status === "completed").length} de ${plan.items.length} completados`}
          />
          <SummaryCard
            label="Pagos"
            value={`${plan.items.filter((i) => i.payment_status === "paid").length} de ${plan.items.length}`}
            sub={
              plan.items.filter((i) => i.payment_status === "invoiced").length > 0
                ? `${plan.items.filter((i) => i.payment_status === "invoiced").length} facturado${plan.items.filter((i) => i.payment_status === "invoiced").length !== 1 ? "s" : ""}`
                : "Procedimientos pagados"
            }
          />
        </div>

        {/* ─── Items Table ─────────────────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary-600" />
              Procedimientos del plan
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {plan.items.length === 0 ? (
              <div className="py-10 text-center text-sm text-[hsl(var(--muted-foreground))]">
                No hay procedimientos en este plan.
              </div>
            ) : (
              <TableWrapper>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[90px]">CUPS</TableHead>
                      <TableHead>Procedimiento</TableHead>
                      <TableHead className="text-right w-[130px]">
                        Est. costo
                      </TableHead>
                      <TableHead className="text-right w-[130px]">
                        Costo real
                      </TableHead>
                      <TableHead className="w-[120px]">Estado</TableHead>
                      <TableHead className="w-[110px]">Pago</TableHead>
                      <TableHead className="w-[100px]">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {plan.items.map((item) => (
                      <PlanItemRow
                        key={item.id}
                        item={item}
                        planStatus={plan.status}
                      />
                    ))}
                  </TableBody>
                </Table>
              </TableWrapper>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ─── Approve Dialog ──────────────────────────────────────────────── */}
      <ApprovalFlow
        open={showApproveDialog}
        onOpenChange={setShowApproveDialog}
        title="Aprobar plan de tratamiento"
        description={`El paciente ${patient.full_name} firma en el área de abajo para aprobar el plan "${plan.name}" y autorizar su ejecución.`}
        onApprove={handleApprove}
        isLoading={isApproving}
      />

      {/* ─── Cancel Dialog ───────────────────────────────────────────────── */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancelar plan de tratamiento</DialogTitle>
            <DialogDescription>
              ¿Estás seguro de que deseas cancelar el plan{" "}
              <span className="font-semibold text-foreground">
                "{plan.name}"
              </span>
              ? Esta acción no puede deshacerse.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col-reverse sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setShowCancelDialog(false)}
              disabled={isCancelling}
            >
              Volver
            </Button>
            <Button
              variant="destructive"
              onClick={handleCancel}
              disabled={isCancelling}
            >
              {isCancelling ? "Cancelando..." : "Cancelar plan"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
