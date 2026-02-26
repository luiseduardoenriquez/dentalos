"use client";

import * as React from "react";
import { Clock, Bell, UserPlus, ChevronLeft, ChevronRight, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  useWaitlist,
  useAddToWaitlist,
  useNotifyWaitlistEntry,
  type WaitlistEntry,
  type WaitlistStatus,
  type WaitlistEntryCreate,
} from "@/lib/hooks/use-waitlist";
import { cn, formatDate } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const DAY_LABELS: Record<number, string> = {
  0: "Lun",
  1: "Mar",
  2: "Mié",
  3: "Jue",
  4: "Vie",
  5: "Sáb",
  6: "Dom",
};

const STATUS_LABELS: Record<WaitlistStatus, string> = {
  waiting: "Esperando",
  notified: "Notificado",
  scheduled: "Agendado",
  expired: "Vencido",
  cancelled: "Cancelado",
};

const STATUS_VARIANT: Record<
  WaitlistStatus,
  "default" | "warning" | "success" | "secondary" | "outline" | "destructive"
> = {
  waiting: "warning",
  notified: "default",
  scheduled: "success",
  expired: "secondary",
  cancelled: "destructive",
};

// ─── Filter tabs ──────────────────────────────────────────────────────────────

type FilterTab = "all" | "waiting" | "notified";

const FILTER_TABS: { key: FilterTab; label: string }[] = [
  { key: "all", label: "Todos" },
  { key: "waiting", label: "Esperando" },
  { key: "notified", label: "Notificado" },
];

// ─── Add to waitlist form ─────────────────────────────────────────────────────

interface AddWaitlistFormProps {
  onClose: () => void;
}

function AddWaitlistForm({ onClose }: AddWaitlistFormProps) {
  const { mutate: addToWaitlist, isPending } = useAddToWaitlist();

  const [patientId, setPatientId] = React.useState("");
  const [procedureType, setProcedureType] = React.useState("");
  const [preferredDays, setPreferredDays] = React.useState<number[]>([]);
  const [timeFrom, setTimeFrom] = React.useState("");
  const [timeTo, setTimeTo] = React.useState("");
  const [validUntil, setValidUntil] = React.useState("");

  function toggleDay(day: number) {
    setPreferredDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day],
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!patientId.trim()) return;

    const payload: WaitlistEntryCreate = {
      patient_id: patientId.trim(),
    };
    if (procedureType) payload.procedure_type = procedureType;
    if (preferredDays.length > 0) payload.preferred_days = preferredDays;
    if (timeFrom) payload.preferred_time_from = timeFrom;
    if (timeTo) payload.preferred_time_to = timeTo;
    if (validUntil) payload.valid_until = validUntil;

    addToWaitlist(payload, { onSuccess: onClose });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {/* Patient ID — in production this would be a patient search combobox */}
      <div className="space-y-1.5">
        <Label htmlFor="wl-patient-id">
          ID del paciente <span className="text-destructive-600">*</span>
        </Label>
        <Input
          id="wl-patient-id"
          placeholder="UUID del paciente"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          required
        />
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          En producción este campo será reemplazado por un buscador de pacientes.
        </p>
      </div>

      {/* Procedure type */}
      <div className="space-y-1.5">
        <Label htmlFor="wl-procedure">Tipo de procedimiento</Label>
        <Input
          id="wl-procedure"
          placeholder="Ej: consulta, limpieza, ortodoncia"
          value={procedureType}
          onChange={(e) => setProcedureType(e.target.value)}
        />
      </div>

      {/* Preferred days */}
      <div className="space-y-2">
        <Label className="text-sm">Días preferidos</Label>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 7 }, (_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => toggleDay(i)}
              className={cn(
                "inline-flex h-8 w-10 items-center justify-center rounded-md text-xs font-medium transition-colors",
                "border border-[hsl(var(--border))]",
                preferredDays.includes(i)
                  ? "bg-primary-600 text-white border-primary-600"
                  : "bg-transparent text-foreground hover:bg-[hsl(var(--muted))]",
              )}
            >
              {DAY_LABELS[i]}
            </button>
          ))}
        </div>
      </div>

      {/* Preferred time range */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="wl-time-from">Hora desde</Label>
          <Input
            id="wl-time-from"
            type="time"
            value={timeFrom}
            onChange={(e) => setTimeFrom(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="wl-time-to">Hora hasta</Label>
          <Input
            id="wl-time-to"
            type="time"
            value={timeTo}
            onChange={(e) => setTimeTo(e.target.value)}
          />
        </div>
      </div>

      {/* Valid until */}
      <div className="space-y-1.5">
        <Label htmlFor="wl-valid-until">Válido hasta</Label>
        <Input
          id="wl-valid-until"
          type="date"
          value={validUntil}
          onChange={(e) => setValidUntil(e.target.value)}
        />
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          Deja en blanco para mantener indefinidamente.
        </p>
      </div>

      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>
          Cancelar
        </Button>
        <Button type="submit" disabled={isPending || !patientId.trim()}>
          {isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Agregando...
            </>
          ) : (
            "Agregar a lista"
          )}
        </Button>
      </DialogFooter>
    </form>
  );
}

// ─── Waitlist entry card ──────────────────────────────────────────────────────

interface EntryCardProps {
  entry: WaitlistEntry;
}

function EntryCard({ entry }: EntryCardProps) {
  const { mutate: notify, isPending: isNotifying } = useNotifyWaitlistEntry();

  const preferredDaysText =
    entry.preferred_days.length > 0
      ? entry.preferred_days.map((d) => DAY_LABELS[d]).join(", ")
      : null;

  const timeWindowText =
    entry.preferred_time_from && entry.preferred_time_to
      ? `${entry.preferred_time_from} – ${entry.preferred_time_to}`
      : null;

  return (
    <div className="group rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-3 transition-shadow hover:shadow-sm">
      {/* ─── Header row ─────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {entry.patient_name ?? "Paciente desconocido"}
          </p>
          {entry.procedure_type && (
            <p className="mt-0.5 truncate text-xs text-[hsl(var(--muted-foreground))]">
              {entry.procedure_type}
            </p>
          )}
        </div>
        <Badge variant={STATUS_VARIANT[entry.status]} className="shrink-0">
          {STATUS_LABELS[entry.status]}
        </Badge>
      </div>

      {/* ─── Details ─────────────────────────────────────────────────────── */}
      <div className="mt-2 space-y-1">
        {entry.preferred_doctor_name && (
          <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
            <span className="font-medium">Dr./Dra.:</span>
            <span className="truncate">{entry.preferred_doctor_name}</span>
          </div>
        )}

        {preferredDaysText && (
          <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
            <Clock className="h-3 w-3 shrink-0" />
            <span>{preferredDaysText}</span>
          </div>
        )}

        {timeWindowText && (
          <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
            <span className="pl-[18px]">{timeWindowText}</span>
          </div>
        )}

        {entry.valid_until && (
          <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
            <span className="font-medium">Válido hasta:</span>
            <span>{formatDate(entry.valid_until)}</span>
          </div>
        )}
      </div>

      {/* ─── Footer row ─────────────────────────────────────────────────── */}
      <div className="mt-3 flex items-center justify-between border-t border-[hsl(var(--border))] pt-2">
        <div className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))]">
          <Bell className="h-3 w-3" />
          <span>
            {entry.notification_count === 0
              ? "Sin notificaciones"
              : `${entry.notification_count} notif.`}
          </span>
          {entry.last_notified_at && (
            <span className="ml-1">
              · {formatDate(entry.last_notified_at)}
            </span>
          )}
        </div>

        {/* Only show Notify button for actionable statuses */}
        {(entry.status === "waiting" || entry.status === "notified") && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={isNotifying}
            onClick={() => notify(entry.id)}
            className="h-7 gap-1.5 px-2 text-xs"
          >
            {isNotifying ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Bell className="h-3 w-3" />
            )}
            Notificar
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Waitlist loading skeleton ────────────────────────────────────────────────

function WaitlistSkeleton() {
  return (
    <div className="space-y-3 p-3">
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="rounded-lg border border-[hsl(var(--border))] p-3 space-y-2">
          <div className="flex justify-between">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-40" />
        </div>
      ))}
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function WaitlistEmpty({ filter }: { filter: FilterTab }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[hsl(var(--muted))] mb-3">
        <Clock className="h-6 w-6 text-[hsl(var(--muted-foreground))]" />
      </div>
      <p className="text-sm font-medium text-foreground">
        {filter === "all"
          ? "No hay pacientes en lista de espera"
          : filter === "waiting"
          ? "No hay pacientes esperando"
          : "No hay pacientes notificados"}
      </p>
      <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
        Usa el botón &quot;Agregar a lista&quot; para añadir un paciente.
      </p>
    </div>
  );
}

// ─── Main panel ───────────────────────────────────────────────────────────────

interface WaitlistPanelProps {
  /** When true, the panel renders in an expanded side-panel style */
  defaultOpen?: boolean;
  className?: string;
}

export function WaitlistPanel({ defaultOpen = true, className }: WaitlistPanelProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);
  const [activeFilter, setActiveFilter] = React.useState<FilterTab>("all");
  const [addDialogOpen, setAddDialogOpen] = React.useState(false);

  const statusFilter =
    activeFilter === "all" ? undefined : (activeFilter as WaitlistStatus);

  const { data, isLoading } = useWaitlist({
    status: statusFilter,
    page_size: 50,
  });

  const entries = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <>
      {/* ─── Collapsed toggle button ────────────────────────────────────── */}
      {!isOpen && (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          aria-label="Abrir lista de espera"
          className={cn(
            "flex h-full w-10 flex-col items-center justify-center gap-2 border-l border-[hsl(var(--border))]",
            "bg-[hsl(var(--card))] text-[hsl(var(--muted-foreground))] hover:text-foreground transition-colors",
            className,
          )}
        >
          <ChevronLeft className="h-4 w-4" />
          <span
            className="text-xs font-medium"
            style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
          >
            Lista de espera
          </span>
          {total > 0 && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary-600 text-[10px] font-bold text-white">
              {total > 99 ? "99+" : total}
            </span>
          )}
        </button>
      )}

      {/* ─── Expanded panel ──────────────────────────────────────────────── */}
      {isOpen && (
        <aside
          className={cn(
            "flex w-72 shrink-0 flex-col border-l border-[hsl(var(--border))] bg-[hsl(var(--card))]",
            className,
          )}
        >
          {/* Panel header */}
          <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-4 py-3">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
              <h2 className="text-sm font-semibold text-foreground">
                Lista de espera
              </h2>
              {total > 0 && (
                <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
                  {total}
                </Badge>
              )}
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              aria-label="Cerrar lista de espera"
              className="rounded p-1 text-[hsl(var(--muted-foreground))] hover:text-foreground transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Filter tabs */}
          <div className="flex border-b border-[hsl(var(--border))] px-3 pt-2">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveFilter(tab.key)}
                className={cn(
                  "pb-2 px-2 text-xs font-medium transition-colors border-b-2",
                  activeFilter === tab.key
                    ? "border-primary-600 text-primary-600 dark:text-primary-400"
                    : "border-transparent text-[hsl(var(--muted-foreground))] hover:text-foreground",
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Entry list — scrollable */}
          <div className="min-h-0 flex-1 overflow-y-auto">
            {isLoading ? (
              <WaitlistSkeleton />
            ) : entries.length === 0 ? (
              <WaitlistEmpty filter={activeFilter} />
            ) : (
              <div className="space-y-2 p-3">
                {entries.map((entry) => (
                  <EntryCard key={entry.id} entry={entry} />
                ))}
              </div>
            )}
          </div>

          <Separator />

          {/* Panel footer */}
          <div className="p-3">
            <Button
              type="button"
              className="w-full gap-2"
              size="sm"
              onClick={() => setAddDialogOpen(true)}
            >
              <UserPlus className="h-4 w-4" />
              Agregar a lista
            </Button>
          </div>
        </aside>
      )}

      {/* ─── Add to waitlist dialog ──────────────────────────────────────── */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent size="default">
          <DialogHeader>
            <DialogTitle>Agregar paciente a lista de espera</DialogTitle>
            <DialogDescription>
              El paciente será notificado automáticamente cuando haya una cita
              disponible que coincida con sus preferencias.
            </DialogDescription>
          </DialogHeader>
          <AddWaitlistForm onClose={() => setAddDialogOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}
