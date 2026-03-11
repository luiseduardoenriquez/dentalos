"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronRight,
  AlertCircle,
  ArrowRight,
  XCircle,
  CalendarDays,
  Stethoscope,
  Package,
  CreditCard,
  FileText,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { EmptyState } from "@/components/empty-state";
import { DataTable } from "@/components/data-table";
import { Pagination } from "@/components/pagination";
import { OrthoStatusBadge } from "@/components/ortho/ortho-status-badge";
import { VisitPaymentBadge } from "@/components/ortho/visit-payment-badge";
import { usePatient } from "@/lib/hooks/use-patients";
import {
  useOrthoCase,
  useOrthoCaseSummary,
  useOrthoBondingRecords,
  useOrthoVisits,
  useOrthoMaterials,
  useTransitionOrthoCase,
} from "@/lib/hooks/use-ortho";
import type {
  BondingRecordListItem,
  OrthoVisitResponse,
  MaterialResponse,
} from "@/lib/hooks/use-ortho";
import {
  ORTHO_STATUS_LABELS,
  APPLIANCE_TYPE_LABELS,
  ANGLE_CLASS_LABELS,
} from "@/lib/validations/ortho";
import { formatDate, formatCurrency, cn } from "@/lib/utils";

// ─── Status Transition Map ────────────────────────────────────────────────────

const TRANSITIONS: Record<string, string[]> = {
  planning: ["bonding"],
  bonding: ["active_treatment"],
  active_treatment: ["retention"],
  retention: ["completed"],
};

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

// ─── Info Row ─────────────────────────────────────────────────────────────────

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="text-sm text-[hsl(var(--muted-foreground))] shrink-0">
        {label}
      </span>
      <span className="text-sm font-medium text-foreground text-right">
        {value ?? "—"}
      </span>
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function CaseDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        {[16, 28, 4, 40, 4, 28, 4, 24].map((w, i) => (
          <Skeleton key={i} className={`h-4 w-${w}`} />
        ))}
      </div>
      <div className="flex items-start justify-between rounded-xl border border-[hsl(var(--border))] p-5">
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-5 w-24" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-32 rounded-md" />
          <Skeleton className="h-9 w-28 rounded-md" />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-10 w-72 rounded-lg" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}

// ─── Tab: Caso (Summary) ──────────────────────────────────────────────────────

function TabCaso({
  patientId,
  caseId,
}: {
  patientId: string;
  caseId: string;
}) {
  const { data: orthoCase } = useOrthoCase(patientId, caseId);
  const { data: summary, isLoading } = useOrthoCaseSummary(patientId, caseId);

  if (isLoading || !orthoCase) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          label="Visitas totales"
          value={String(summary?.total_visits ?? 0)}
          sub={
            summary
              ? `${summary.visits_paid} pagadas · ${summary.visits_pending} pendientes`
              : undefined
          }
        />
        <SummaryCard
          label="Pagos recibidos"
          value={formatCurrency(summary?.total_collected ?? 0, "COP")}
          sub={`de ${formatCurrency(summary?.total_expected ?? 0, "COP")} esperados`}
        />
        <SummaryCard
          label="Saldo pendiente"
          value={formatCurrency(summary?.balance_remaining ?? 0, "COP")}
          sub={
            summary?.next_visit_date
              ? `Próx. visita: ${formatDate(summary.next_visit_date)}`
              : undefined
          }
        />
        <SummaryCard
          label="Materiales usados"
          value={String(summary?.materials_count ?? 0)}
          sub={
            summary?.last_visit_date
              ? `Última visita: ${formatDate(summary.last_visit_date)}`
              : undefined
          }
        />
      </div>

      {/* Case info cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Clasificación */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Stethoscope className="h-4 w-4 text-primary-600" />
              Clasificación
            </CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-[hsl(var(--border))]">
            <InfoRow
              label="Clase de Angle"
              value={
                orthoCase.angle_class
                  ? (ANGLE_CLASS_LABELS[orthoCase.angle_class] ??
                    orthoCase.angle_class)
                  : "—"
              }
            />
            <InfoRow
              label="Tipo de maloclusión"
              value={orthoCase.malocclusion_type ?? "—"}
            />
          </CardContent>
        </Card>

        {/* Aparatología */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <CalendarDays className="h-4 w-4 text-primary-600" />
              Aparatología
            </CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-[hsl(var(--border))]">
            <InfoRow
              label="Tipo"
              value={
                APPLIANCE_TYPE_LABELS[orthoCase.appliance_type] ??
                orthoCase.appliance_type
              }
            />
            <InfoRow
              label="Duración estimada"
              value={
                orthoCase.estimated_duration_months != null
                  ? `${orthoCase.estimated_duration_months} meses`
                  : "—"
              }
            />
          </CardContent>
        </Card>

        {/* Financiero */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-primary-600" />
              Financiero
            </CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-[hsl(var(--border))]">
            <InfoRow
              label="Costo estimado"
              value={formatCurrency(orthoCase.total_cost_estimated, "COP")}
            />
            <InfoRow
              label="Pago inicial"
              value={formatCurrency(orthoCase.initial_payment, "COP")}
            />
            <InfoRow
              label="Cuota mensual"
              value={formatCurrency(orthoCase.monthly_payment, "COP")}
            />
          </CardContent>
        </Card>
      </div>

      {/* Notes */}
      {orthoCase.notes && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary-600" />
              Notas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
              {orthoCase.notes}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Tab: Aparatología (Bonding Records) ─────────────────────────────────────

function TabAparatologia({
  patientId,
  caseId,
}: {
  patientId: string;
  caseId: string;
}) {
  const router = useRouter();
  const [page, setPage] = React.useState(1);
  const PAGE_SIZE = 10;

  const { data, isLoading } = useOrthoBondingRecords(
    patientId,
    caseId,
    page,
    PAGE_SIZE,
  );

  const columns = React.useMemo(
    () => [
      {
        key: "created_at" as keyof BondingRecordListItem,
        header: "Fecha",
        cell: (row: BondingRecordListItem) => formatDate(row.created_at),
      },
      {
        key: "recorded_by" as keyof BondingRecordListItem,
        header: "Registrado por",
        cell: (row: BondingRecordListItem) => (
          <span className="font-mono text-xs text-[hsl(var(--muted-foreground))]">
            {row.recorded_by.slice(0, 8)}…
          </span>
        ),
      },
      {
        key: "tooth_count" as keyof BondingRecordListItem,
        header: "Dientes",
        cell: (row: BondingRecordListItem) => (
          <span className="font-medium">{row.tooth_count} dientes</span>
        ),
      },
    ],
    [],
  );

  return (
    <div className="space-y-4">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">
          Registros de aparatología
        </h2>
        <Button
          size="sm"
          onClick={() =>
            router.push(
              `/patients/${patientId}/ortho/${caseId}/new-bonding`,
            )
          }
        >
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Nuevo registro
        </Button>
      </div>

      {/* Table */}
      {!isLoading && data?.items.length === 0 ? (
        <EmptyState
          icon={Stethoscope}
          title="Sin registros de aparatología"
          description="Aún no hay registros de cementado para este caso. Agrega el primero."
          action={{
            label: "Nuevo registro",
            onClick: () =>
              router.push(
                `/patients/${patientId}/ortho/${caseId}/new-bonding`,
              ),
          }}
        />
      ) : (
        <>
          <DataTable<BondingRecordListItem>
            columns={columns}
            data={data?.items ?? []}
            loading={isLoading}
            skeletonRows={3}
            rowKey="id"
          />
          {data && data.total > PAGE_SIZE && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={data.total}
              onChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}

// ─── Tab: Visitas ─────────────────────────────────────────────────────────────

function TabVisitas({
  patientId,
  caseId,
}: {
  patientId: string;
  caseId: string;
}) {
  const router = useRouter();
  const [page, setPage] = React.useState(1);
  const PAGE_SIZE = 10;

  const { data, isLoading } = useOrthoVisits(
    patientId,
    caseId,
    page,
    PAGE_SIZE,
  );

  const columns = React.useMemo(
    () => [
      {
        key: "visit_number" as keyof OrthoVisitResponse,
        header: "#",
        headerClassName: "w-[60px]",
        cell: (row: OrthoVisitResponse) => (
          <span className="font-medium tabular-nums">{row.visit_number}</span>
        ),
      },
      {
        key: "visit_date" as keyof OrthoVisitResponse,
        header: "Fecha",
        cell: (row: OrthoVisitResponse) => formatDate(row.visit_date),
      },
      {
        key: "wire_upper" as keyof OrthoVisitResponse,
        header: "Arco sup.",
        cell: (row: OrthoVisitResponse) => (
          <span className="text-[hsl(var(--muted-foreground))]">
            {row.wire_upper ?? "—"}
          </span>
        ),
      },
      {
        key: "wire_lower" as keyof OrthoVisitResponse,
        header: "Arco inf.",
        cell: (row: OrthoVisitResponse) => (
          <span className="text-[hsl(var(--muted-foreground))]">
            {row.wire_lower ?? "—"}
          </span>
        ),
      },
      {
        key: "elastics" as keyof OrthoVisitResponse,
        header: "Elásticos",
        cell: (row: OrthoVisitResponse) => (
          <span className="text-[hsl(var(--muted-foreground))]">
            {row.elastics ?? "—"}
          </span>
        ),
      },
      {
        key: "payment_status" as keyof OrthoVisitResponse,
        header: "Pago",
        cell: (row: OrthoVisitResponse) => (
          <VisitPaymentBadge status={row.payment_status} />
        ),
      },
      {
        key: "payment_amount" as keyof OrthoVisitResponse,
        header: "Monto",
        headerClassName: "text-right",
        cellClassName: "text-right tabular-nums",
        cell: (row: OrthoVisitResponse) =>
          row.payment_amount > 0
            ? formatCurrency(row.payment_amount, "COP")
            : "—",
      },
    ],
    [],
  );

  return (
    <div className="space-y-4">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">
          Visitas de control
        </h2>
        <Button
          size="sm"
          onClick={() =>
            router.push(
              `/patients/${patientId}/ortho/${caseId}/new-visit`,
            )
          }
        >
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Nueva visita
        </Button>
      </div>

      {/* Table */}
      {!isLoading && data?.items.length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="Sin visitas registradas"
          description="No hay visitas de control para este caso. Registra la primera."
          action={{
            label: "Nueva visita",
            onClick: () =>
              router.push(
                `/patients/${patientId}/ortho/${caseId}/new-visit`,
              ),
          }}
        />
      ) : (
        <>
          <DataTable<OrthoVisitResponse>
            columns={columns}
            data={data?.items ?? []}
            loading={isLoading}
            skeletonRows={5}
            rowKey="id"
          />
          {data && data.total > PAGE_SIZE && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={data.total}
              onChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}

// ─── Tab: Materiales ──────────────────────────────────────────────────────────

function TabMateriales({
  patientId,
  caseId,
}: {
  patientId: string;
  caseId: string;
}) {
  const [page, setPage] = React.useState(1);
  const PAGE_SIZE = 10;

  const { data, isLoading } = useOrthoMaterials(
    patientId,
    caseId,
    page,
    PAGE_SIZE,
  );

  const columns = React.useMemo(
    () => [
      {
        key: "inventory_item_id" as keyof MaterialResponse,
        header: "Material",
        cell: (row: MaterialResponse) => (
          <span className="font-mono text-xs text-[hsl(var(--muted-foreground))]">
            {row.inventory_item_id.slice(0, 8)}…
          </span>
        ),
      },
      {
        key: "visit_id" as keyof MaterialResponse,
        header: "Visita",
        cell: (row: MaterialResponse) =>
          row.visit_id ? (
            <span className="font-mono text-xs text-[hsl(var(--muted-foreground))]">
              {row.visit_id.slice(0, 8)}…
            </span>
          ) : (
            <span className="text-[hsl(var(--muted-foreground))]">General</span>
          ),
      },
      {
        key: "quantity_used" as keyof MaterialResponse,
        header: "Cantidad",
        cell: (row: MaterialResponse) => (
          <span className="font-medium tabular-nums">{row.quantity_used}</span>
        ),
      },
      {
        key: "notes" as keyof MaterialResponse,
        header: "Notas",
        cell: (row: MaterialResponse) => (
          <span className="text-[hsl(var(--muted-foreground))] truncate max-w-[200px] block">
            {row.notes ?? "—"}
          </span>
        ),
      },
      {
        key: "created_at" as keyof MaterialResponse,
        header: "Fecha",
        cell: (row: MaterialResponse) => formatDate(row.created_at),
      },
    ],
    [],
  );

  return (
    <div className="space-y-4">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">
          Materiales consumidos
        </h2>
      </div>

      {/* Table */}
      {!isLoading && data?.items.length === 0 ? (
        <EmptyState
          icon={Package}
          title="Sin materiales registrados"
          description="No hay materiales consumidos registrados para este caso."
        />
      ) : (
        <>
          <DataTable<MaterialResponse>
            columns={columns}
            data={data?.items ?? []}
            loading={isLoading}
            skeletonRows={4}
            rowKey="id"
          />
          {data && data.total > PAGE_SIZE && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={data.total}
              onChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OrthoCaseDetailPage() {
  const params = useParams<{ id: string; caseId: string }>();
  const { id: patientId, caseId } = params;

  const [showTransitionDialog, setShowTransitionDialog] = React.useState(false);
  const [showCancelDialog, setShowCancelDialog] = React.useState(false);
  const [targetStatus, setTargetStatus] = React.useState<string>("");

  const { data: patient, isLoading: isLoadingPatient } = usePatient(patientId);
  const { data: orthoCase, isLoading: isLoadingCase } = useOrthoCase(
    patientId,
    caseId,
  );
  const { mutate: transition, isPending: isTransitioning } =
    useTransitionOrthoCase(patientId);

  const isLoading = isLoadingPatient || isLoadingCase;

  // Derive available transitions from current status
  const availableTransitions =
    orthoCase ? (TRANSITIONS[orthoCase.status] ?? []) : [];

  const canTransition =
    orthoCase &&
    !["completed", "cancelled"].includes(orthoCase.status) &&
    availableTransitions.length > 0;

  const canCancel =
    orthoCase && !["completed", "cancelled"].includes(orthoCase.status);

  function handleTransitionConfirm() {
    if (!targetStatus) return;
    transition(
      { caseId, targetStatus },
      {
        onSuccess: () => {
          setShowTransitionDialog(false);
          setTargetStatus("");
        },
      },
    );
  }

  function handleCancelConfirm() {
    transition(
      { caseId, targetStatus: "cancelled" },
      {
        onSuccess: () => {
          setShowCancelDialog(false);
        },
      },
    );
  }

  function openTransitionDialog() {
    // Pre-select the only available transition if there's just one
    if (availableTransitions.length === 1) {
      setTargetStatus(availableTransitions[0]);
    }
    setShowTransitionDialog(true);
  }

  if (isLoading) {
    return <CaseDetailSkeleton />;
  }

  if (!patient || !orthoCase) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Caso no encontrado"
        description="El caso de ortodoncia que buscas no existe o no tienes permiso para verlo."
        action={{
          label: "Volver a ortodoncia",
          href: `/patients/${patientId}/ortho`,
        }}
      />
    );
  }

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
            href={`/patients/${patientId}/ortho`}
            className="hover:text-foreground transition-colors"
          >
            Ortodoncia
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground font-medium">
            {orthoCase.case_number}
          </span>
        </nav>

        {/* ─── Header ──────────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between rounded-xl border border-[hsl(var(--border))] p-5 bg-[hsl(var(--card))]">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold text-foreground">
                {orthoCase.case_number}
              </h1>
              <OrthoStatusBadge status={orthoCase.status} />
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Creado el{" "}
              <span className="font-medium text-foreground">
                {formatDate(orthoCase.created_at)}
              </span>
              {orthoCase.actual_start_date && (
                <>
                  {" · "}Inicio:{" "}
                  <span className="font-medium text-foreground">
                    {formatDate(orthoCase.actual_start_date)}
                  </span>
                </>
              )}
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2 sm:flex-col sm:items-end md:flex-row">
            {canTransition && (
              <Button size="sm" onClick={openTransitionDialog}>
                <ArrowRight className="mr-1.5 h-3.5 w-3.5" />
                Siguiente estado
              </Button>
            )}
            {canCancel && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowCancelDialog(true)}
                disabled={isTransitioning}
              >
                <XCircle className="mr-1.5 h-3.5 w-3.5" />
                Cancelar caso
              </Button>
            )}
          </div>
        </div>

        {/* ─── Tabs ────────────────────────────────────────────────────────── */}
        <Tabs defaultValue="caso" className="space-y-4">
          <TabsList>
            <TabsTrigger value="caso">Caso</TabsTrigger>
            <TabsTrigger value="aparatologia">Aparatología</TabsTrigger>
            <TabsTrigger value="visitas">Visitas</TabsTrigger>
            <TabsTrigger value="materiales">Materiales</TabsTrigger>
          </TabsList>

          <TabsContent value="caso">
            <TabCaso patientId={patientId} caseId={caseId} />
          </TabsContent>

          <TabsContent value="aparatologia">
            <TabAparatologia patientId={patientId} caseId={caseId} />
          </TabsContent>

          <TabsContent value="visitas">
            <TabVisitas patientId={patientId} caseId={caseId} />
          </TabsContent>

          <TabsContent value="materiales">
            <TabMateriales patientId={patientId} caseId={caseId} />
          </TabsContent>
        </Tabs>
      </div>

      {/* ─── Transition Dialog ───────────────────────────────────────────── */}
      <Dialog
        open={showTransitionDialog}
        onOpenChange={(open) => {
          setShowTransitionDialog(open);
          if (!open) setTargetStatus("");
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cambiar estado del caso</DialogTitle>
            <DialogDescription>
              Selecciona el estado al que deseas avanzar el caso{" "}
              <span className="font-semibold text-foreground">
                {orthoCase.case_number}
              </span>
              . Esta acción actualizará el flujo del tratamiento.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2 py-2">
            <label
              htmlFor="target-status-select"
              className="text-sm font-medium text-foreground"
            >
              Nuevo estado
            </label>
            <Select value={targetStatus} onValueChange={setTargetStatus}>
              <SelectTrigger id="target-status-select">
                <SelectValue placeholder="Selecciona un estado" />
              </SelectTrigger>
              <SelectContent>
                {availableTransitions.map((s) => (
                  <SelectItem key={s} value={s}>
                    {ORTHO_STATUS_LABELS[s] ?? s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter className="flex-col-reverse sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setShowTransitionDialog(false);
                setTargetStatus("");
              }}
              disabled={isTransitioning}
            >
              Volver
            </Button>
            <Button
              onClick={handleTransitionConfirm}
              disabled={!targetStatus || isTransitioning}
            >
              {isTransitioning ? "Actualizando..." : "Confirmar cambio"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Cancel Dialog ───────────────────────────────────────────────── */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancelar caso de ortodoncia</DialogTitle>
            <DialogDescription>
              ¿Estás seguro de que deseas cancelar el caso{" "}
              <span className="font-semibold text-foreground">
                {orthoCase.case_number}
              </span>
              ? Esta acción no puede deshacerse.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col-reverse sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setShowCancelDialog(false)}
              disabled={isTransitioning}
            >
              Volver
            </Button>
            <Button
              variant="destructive"
              onClick={handleCancelConfirm}
              disabled={isTransitioning}
            >
              {isTransitioning ? "Cancelando..." : "Cancelar caso"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
