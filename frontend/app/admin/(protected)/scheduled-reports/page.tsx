"use client";

import { useState } from "react";
import {
  useScheduledReports,
  useCreateScheduledReport,
  useUpdateScheduledReport,
  useDeleteScheduledReport,
  type ScheduledReportResponse,
} from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

// ─── Constants ─────────────────────────────────────────────────────────────────

const REPORT_TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "revenue", label: "Ingresos" },
  { value: "tenant_activity", label: "Actividad de clínicas" },
  { value: "compliance", label: "Cumplimiento" },
  { value: "health", label: "Salud del sistema" },
];

const SCHEDULE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "daily", label: "Diario" },
  { value: "weekly", label: "Semanal" },
  { value: "monthly", label: "Mensual" },
];

const REPORT_TYPE_LABELS: Record<string, string> = {
  revenue: "Ingresos",
  tenant_activity: "Actividad de clínicas",
  compliance: "Cumplimiento",
  health: "Salud del sistema",
};

const SCHEDULE_LABELS: Record<string, string> = {
  daily: "Diario",
  weekly: "Semanal",
  monthly: "Mensual",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("es-419", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function parseRecipients(raw: string): string[] {
  return raw
    .split(",")
    .map((r) => r.trim())
    .filter((r) => r.length > 0);
}

// ─── Type Badge ───────────────────────────────────────────────────────────────

function ReportTypeBadge({ type }: { type: string }) {
  const label = REPORT_TYPE_LABELS[type] ?? type;

  if (type === "revenue") {
    return (
      <Badge
        variant="outline"
        className="border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300 text-xs"
      >
        {label}
      </Badge>
    );
  }

  if (type === "tenant_activity") {
    return (
      <Badge
        variant="outline"
        className="border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300 text-xs"
      >
        {label}
      </Badge>
    );
  }

  if (type === "compliance") {
    return (
      <Badge
        variant="outline"
        className="border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300 text-xs"
      >
        {label}
      </Badge>
    );
  }

  if (type === "health") {
    return (
      <Badge
        variant="outline"
        className="border-purple-300 bg-purple-50 text-purple-700 dark:border-purple-700 dark:bg-purple-950 dark:text-purple-300 text-xs"
      >
        {label}
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className="text-xs">
      {label}
    </Badge>
  );
}

// ─── Schedule Badge ───────────────────────────────────────────────────────────

function ScheduleBadge({ schedule }: { schedule: string }) {
  const label = SCHEDULE_LABELS[schedule] ?? schedule;
  return (
    <Badge variant="secondary" className="text-xs">
      {label}
    </Badge>
  );
}

// ─── Recipient Pills ──────────────────────────────────────────────────────────

function RecipientPills({ recipients }: { recipients: string[] }) {
  if (recipients.length === 0) {
    return (
      <span className="text-sm text-[hsl(var(--muted-foreground))]">—</span>
    );
  }

  const visible = recipients.slice(0, 2);
  const overflow = recipients.length - visible.length;

  return (
    <div className="flex flex-wrap items-center gap-1">
      {visible.map((email) => (
        <span
          key={email}
          title={email}
          className={cn(
            "inline-flex max-w-[140px] truncate rounded-full px-2 py-0.5 text-xs",
            "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]",
            "border border-[hsl(var(--border))]",
          )}
        >
          {email}
        </span>
      ))}
      {overflow > 0 && (
        <span
          className="text-xs text-[hsl(var(--muted-foreground))]"
          title={recipients.slice(2).join(", ")}
        >
          +{overflow} más
        </span>
      )}
    </div>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function ReportsLoadingSkeleton() {
  return (
    <Card>
      <CardContent className="p-0">
        <div className="divide-y divide-[hsl(var(--border))]">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-4 px-6 py-4">
              <Skeleton className="h-4 w-36" />
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-5 w-16 ml-auto" />
              <Skeleton className="h-8 w-14" />
              <Skeleton className="h-8 w-14" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Report Form State ────────────────────────────────────────────────────────

interface ReportFormState {
  name: string;
  report_type: string;
  schedule: string;
  recipientInput: string;
  recipients: string[];
  is_active: boolean;
}

const EMPTY_FORM: ReportFormState = {
  name: "",
  report_type: "revenue",
  schedule: "weekly",
  recipientInput: "",
  recipients: [],
  is_active: true,
};

// ─── Report Form Fields ───────────────────────────────────────────────────────

interface ReportFormFieldsProps {
  state: ReportFormState;
  onChange: (updates: Partial<ReportFormState>) => void;
}

function ReportFormFields({ state, onChange }: ReportFormFieldsProps) {
  function handleAddRecipient() {
    const emails = parseRecipients(state.recipientInput);
    if (emails.length === 0) return;
    const merged = Array.from(new Set([...state.recipients, ...emails]));
    onChange({ recipients: merged, recipientInput: "" });
  }

  function handleRemoveRecipient(email: string) {
    onChange({ recipients: state.recipients.filter((r) => r !== email) });
  }

  function handleRecipientKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddRecipient();
    }
  }

  return (
    <div className="grid gap-4 py-2">
      {/* Report name */}
      <div className="space-y-1.5">
        <Label htmlFor="report-name">
          Nombre <span className="text-red-500">*</span>
        </Label>
        <Input
          id="report-name"
          type="text"
          value={state.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="ej: Reporte semanal de ingresos"
        />
      </div>

      {/* Report type */}
      <div className="space-y-1.5">
        <Label htmlFor="report-type">Tipo de reporte</Label>
        <select
          id="report-type"
          value={state.report_type}
          onChange={(e) => onChange({ report_type: e.target.value })}
          className={cn(
            "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
            "px-3 py-2 text-sm text-foreground shadow-sm",
            "focus:outline-none focus:ring-2 focus:ring-primary-600",
          )}
        >
          {REPORT_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Schedule */}
      <div className="space-y-1.5">
        <Label htmlFor="report-schedule">Frecuencia</Label>
        <select
          id="report-schedule"
          value={state.schedule}
          onChange={(e) => onChange({ schedule: e.target.value })}
          className={cn(
            "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
            "px-3 py-2 text-sm text-foreground shadow-sm",
            "focus:outline-none focus:ring-2 focus:ring-primary-600",
          )}
        >
          {SCHEDULE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Recipients */}
      <div className="space-y-1.5">
        <Label htmlFor="report-recipients">Destinatarios</Label>
        <div className="flex gap-2">
          <Input
            id="report-recipients"
            type="text"
            value={state.recipientInput}
            onChange={(e) => onChange({ recipientInput: e.target.value })}
            onKeyDown={handleRecipientKeyDown}
            placeholder="email@ejemplo.com, otro@ejemplo.com"
            className="text-sm"
            aria-describedby="report-recipients-hint"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddRecipient}
            disabled={!state.recipientInput.trim()}
            className="shrink-0"
          >
            Agregar
          </Button>
        </div>
        <p
          id="report-recipients-hint"
          className="text-xs text-[hsl(var(--muted-foreground))]"
        >
          Separa multiples correos con comas o presiona Enter para agregar.
        </p>

        {/* Recipient pills */}
        {state.recipients.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {state.recipients.map((email) => (
              <span
                key={email}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs",
                  "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]",
                  "border border-[hsl(var(--border))]",
                )}
              >
                {email}
                <button
                  type="button"
                  aria-label={`Eliminar ${email}`}
                  onClick={() => handleRemoveRecipient(email)}
                  className="ml-0.5 rounded-full p-0.5 hover:bg-[hsl(var(--border))] transition-colors"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className="h-3 w-3"
                    aria-hidden="true"
                  >
                    <path d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z" />
                  </svg>
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Active toggle */}
      <div className="flex items-center gap-2 pt-1">
        <Checkbox
          id="report-active"
          checked={state.is_active}
          onCheckedChange={(checked) =>
            onChange({ is_active: checked === true })
          }
        />
        <Label htmlFor="report-active" className="cursor-pointer">
          Reporte activo
        </Label>
      </div>
    </div>
  );
}

// ─── Create Report Dialog ─────────────────────────────────────────────────────

interface CreateReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function CreateReportDialog({ open, onOpenChange }: CreateReportDialogProps) {
  const { success, error } = useToast();
  const createReport = useCreateScheduledReport();
  const [form, setForm] = useState<ReportFormState>(EMPTY_FORM);

  // Reset form each time dialog opens
  function handleOpenChange(nextOpen: boolean) {
    if (nextOpen) setForm(EMPTY_FORM);
    onOpenChange(nextOpen);
  }

  function handleCreate() {
    if (!form.name.trim()) return;

    createReport.mutate(
      {
        name: form.name.trim(),
        report_type: form.report_type,
        schedule: form.schedule,
        recipients: form.recipients,
        is_active: form.is_active,
      },
      {
        onSuccess: () => {
          success(
            "Reporte creado",
            `"${form.name.trim()}" se creó correctamente.`,
          );
          onOpenChange(false);
        },
        onError: () => {
          error(
            "Error al crear",
            "No se pudo crear el reporte. Intenta de nuevo.",
          );
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Crear reporte programado</DialogTitle>
          <DialogDescription>
            Los reportes se envían automáticamente por email según la frecuencia
            configurada.
          </DialogDescription>
        </DialogHeader>

        <ReportFormFields
          state={form}
          onChange={(updates) => setForm((prev) => ({ ...prev, ...updates }))}
        />

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={createReport.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleCreate}
            disabled={createReport.isPending || !form.name.trim()}
          >
            {createReport.isPending ? "Creando..." : "Crear Reporte"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Report Dialog ───────────────────────────────────────────────────────

interface EditReportDialogProps {
  report: ScheduledReportResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function EditReportDialog({
  report,
  open,
  onOpenChange,
}: EditReportDialogProps) {
  const { success, error } = useToast();
  const updateReport = useUpdateScheduledReport();

  const [form, setForm] = useState<ReportFormState>({
    name: report.name,
    report_type: report.report_type,
    schedule: report.schedule,
    recipientInput: "",
    recipients: report.recipients ?? [],
    is_active: report.is_active,
  });

  // Sync when dialog opens with a new report
  function handleOpenChange(nextOpen: boolean) {
    if (nextOpen) {
      setForm({
        name: report.name,
        report_type: report.report_type,
        schedule: report.schedule,
        recipientInput: "",
        recipients: report.recipients ?? [],
        is_active: report.is_active,
      });
    }
    onOpenChange(nextOpen);
  }

  function handleSave() {
    updateReport.mutate(
      {
        id: report.id,
        name: form.name.trim(),
        report_type: form.report_type,
        schedule: form.schedule,
        recipients: form.recipients,
        is_active: form.is_active,
      },
      {
        onSuccess: () => {
          success(
            "Reporte actualizado",
            "Los cambios se guardaron correctamente.",
          );
          onOpenChange(false);
        },
        onError: () => {
          error(
            "Error al guardar",
            "No se pudo actualizar el reporte. Intenta de nuevo.",
          );
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Editar reporte programado</DialogTitle>
          <DialogDescription>
            Modifica la configuración del reporte. Los cambios aplican a partir
            del próximo envío.
          </DialogDescription>
        </DialogHeader>

        <ReportFormFields
          state={form}
          onChange={(updates) => setForm((prev) => ({ ...prev, ...updates }))}
        />

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={updateReport.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
            disabled={updateReport.isPending || !form.name.trim()}
          >
            {updateReport.isPending ? "Guardando..." : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Delete Confirm Dialog ────────────────────────────────────────────────────

interface DeleteReportDialogProps {
  report: ScheduledReportResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function DeleteReportDialog({
  report,
  open,
  onOpenChange,
}: DeleteReportDialogProps) {
  const { success, error } = useToast();
  const deleteReport = useDeleteScheduledReport();

  function handleDelete() {
    deleteReport.mutate(report.id, {
      onSuccess: () => {
        success("Reporte eliminado", `"${report.name}" fue eliminado.`);
        onOpenChange(false);
      },
      onError: () => {
        error(
          "Error al eliminar",
          "No se pudo eliminar el reporte. Intenta de nuevo.",
        );
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Eliminar reporte</DialogTitle>
          <DialogDescription>
            Esta acción no se puede deshacer. El reporte{" "}
            <span className="font-semibold text-foreground">
              &ldquo;{report.name}&rdquo;
            </span>{" "}
            será eliminado permanentemente y dejará de enviarse.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={deleteReport.isPending}
          >
            Cancelar
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteReport.isPending}
          >
            {deleteReport.isPending ? "Eliminando..." : "Eliminar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminScheduledReportsPage() {
  const { data, isLoading, isError, refetch } = useScheduledReports();
  const [createOpen, setCreateOpen] = useState(false);
  const [editingReport, setEditingReport] =
    useState<ScheduledReportResponse | null>(null);
  const [deletingReport, setDeletingReport] =
    useState<ScheduledReportResponse | null>(null);

  const reports = data?.items ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Reportes Programados
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Configurar reportes automáticos por email
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="shrink-0">
          Crear Reporte
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && <ReportsLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar los reportes programados. Verifica la conexion con
              la API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Reports table */}
      {!isLoading && !isError && (
        <>
          {reports.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-2 py-16 text-center">
                <p className="text-base font-medium text-[hsl(var(--muted-foreground))]">
                  No hay reportes programados
                </p>
                <p className="text-sm text-[hsl(var(--muted-foreground))] opacity-70">
                  Crea el primero para comenzar a enviar reportes automáticos.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => setCreateOpen(true)}
                >
                  Crear primer reporte
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
              <CardHeader className="pb-0">
                <CardTitle className="text-base">
                  {reports.length}{" "}
                  {reports.length === 1
                    ? "reporte configurado"
                    : "reportes configurados"}
                </CardTitle>
                <CardDescription>
                  Los reportes activos se envían automáticamente según su
                  frecuencia.
                </CardDescription>
              </CardHeader>
              <CardContent className="mt-4 p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="min-w-[160px]">Nombre</TableHead>
                        <TableHead className="min-w-[140px]">Tipo</TableHead>
                        <TableHead className="min-w-[100px]">
                          Frecuencia
                        </TableHead>
                        <TableHead className="min-w-[180px]">
                          Destinatarios
                        </TableHead>
                        <TableHead className="min-w-[90px]">Estado</TableHead>
                        <TableHead className="min-w-[150px]">
                          Última ejecución
                        </TableHead>
                        <TableHead className="min-w-[150px]">
                          Próxima ejecución
                        </TableHead>
                        <TableHead className="text-right min-w-[120px]">
                          Acciones
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {reports.map((report) => (
                        <TableRow key={report.id}>
                          {/* Name */}
                          <TableCell className="font-medium">
                            {report.name}
                          </TableCell>

                          {/* Report type badge */}
                          <TableCell>
                            <ReportTypeBadge type={report.report_type} />
                          </TableCell>

                          {/* Schedule badge */}
                          <TableCell>
                            <ScheduleBadge schedule={report.schedule} />
                          </TableCell>

                          {/* Recipients as pills */}
                          <TableCell>
                            <RecipientPills
                              recipients={report.recipients ?? []}
                            />
                          </TableCell>

                          {/* Active / inactive status */}
                          <TableCell>
                            <Badge
                              variant={
                                report.is_active ? "success" : "secondary"
                              }
                            >
                              {report.is_active ? "Activo" : "Inactivo"}
                            </Badge>
                          </TableCell>

                          {/* Last run */}
                          <TableCell className="text-sm text-[hsl(var(--muted-foreground))] tabular-nums">
                            {formatDateTime(report.last_run_at)}
                          </TableCell>

                          {/* Next run */}
                          <TableCell className="text-sm text-[hsl(var(--muted-foreground))] tabular-nums">
                            {formatDateTime(report.next_run_at)}
                          </TableCell>

                          {/* Actions */}
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setEditingReport(report)}
                              >
                                Editar
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                                onClick={() => setDeletingReport(report)}
                              >
                                Eliminar
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Create dialog */}
      <CreateReportDialog open={createOpen} onOpenChange={setCreateOpen} />

      {/* Edit dialog — only mounts when a report is selected */}
      {editingReport && (
        <EditReportDialog
          report={editingReport}
          open={editingReport !== null}
          onOpenChange={(open) => {
            if (!open) setEditingReport(null);
          }}
        />
      )}

      {/* Delete confirm dialog — only mounts when a report is selected */}
      {deletingReport && (
        <DeleteReportDialog
          report={deletingReport}
          open={deletingReport !== null}
          onOpenChange={(open) => {
            if (!open) setDeletingReport(null);
          }}
        />
      )}
    </div>
  );
}
