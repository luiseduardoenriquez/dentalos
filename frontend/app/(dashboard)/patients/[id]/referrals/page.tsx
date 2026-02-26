"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronRight, UserPlus, Users, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Pagination } from "@/components/pagination";
import { usePatient } from "@/lib/hooks/use-patients";
import {
  usePatientReferrals,
  useCreateReferral,
  useUpdateReferral,
  type ReferralResponse,
} from "@/lib/hooks/use-referrals";
import { formatDate } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  pending: "Pendiente",
  accepted: "Aceptada",
  completed: "Completada",
  declined: "Rechazada",
};

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "success" | "destructive"> = {
  pending: "default",
  accepted: "success",
  completed: "secondary",
  declined: "destructive",
};

const PRIORITY_LABELS: Record<string, string> = {
  urgent: "Urgente",
  normal: "Normal",
  low: "Baja",
};

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function ReferralsListSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-9 w-36" />
      </div>
      <div className="rounded-xl border">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-0">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Column Definitions ─────────────────────────────────────────────────────

function buildColumns(onAction: (id: string, status: string) => void): ColumnDef<ReferralResponse>[] {
  return [
    {
      key: "to_doctor_name",
      header: "Doctor destino",
      sortable: false,
      cell: (row) => (
        <div>
          <span className="text-sm font-medium text-foreground">{row.to_doctor_name || "—"}</span>
          {row.specialty && (
            <span className="block text-xs text-[hsl(var(--muted-foreground))]">{row.specialty}</span>
          )}
        </div>
      ),
    },
    {
      key: "reason",
      header: "Motivo",
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))] truncate max-w-[200px] inline-block">
          {row.reason}
        </span>
      ),
    },
    {
      key: "priority",
      header: "Prioridad",
      cell: (row) => (
        <Badge variant={row.priority === "urgent" ? "destructive" : "secondary"} className="text-xs">
          {PRIORITY_LABELS[row.priority] ?? row.priority}
        </Badge>
      ),
    },
    {
      key: "status",
      header: "Estado",
      cell: (row) => (
        <Badge variant={STATUS_VARIANTS[row.status] ?? "default"} className="text-xs">
          {STATUS_LABELS[row.status] ?? row.status}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: "Fecha",
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))]">
          {formatDate(row.created_at)}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      cell: (row) =>
        row.status === "pending" ? (
          <div className="flex gap-1">
            <Button size="sm" variant="outline" onClick={() => onAction(row.id, "accepted")}>
              Aceptar
            </Button>
            <Button size="sm" variant="ghost" onClick={() => onAction(row.id, "declined")}>
              Rechazar
            </Button>
          </div>
        ) : row.status === "accepted" ? (
          <Button size="sm" variant="outline" onClick={() => onAction(row.id, "completed")}>
            Completar
          </Button>
        ) : null,
    },
  ];
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PatientReferralsPage() {
  const params = useParams<{ id: string }>();
  const patientId = params.id;

  const [page, setPage] = React.useState(1);
  const [showCreateForm, setShowCreateForm] = React.useState(false);
  const [toDoctorId, setToDoctorId] = React.useState("");
  const [reason, setReason] = React.useState("");
  const [priority, setPriority] = React.useState("normal");
  const [specialty, setSpecialty] = React.useState("");

  const { data: patient } = usePatient(patientId);
  const { data, isLoading, isError } = usePatientReferrals(patientId, page, 20);
  const createReferral = useCreateReferral(patientId);
  const updateReferral = useUpdateReferral();

  function handleAction(referralId: string, status: string) {
    updateReferral.mutate({ referralId, status });
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!toDoctorId.trim() || !reason.trim()) return;
    createReferral.mutate(
      {
        to_doctor_id: toDoctorId,
        reason,
        priority,
        specialty: specialty || undefined,
      },
      {
        onSuccess: () => {
          setToDoctorId("");
          setReason("");
          setPriority("normal");
          setSpecialty("");
          setShowCreateForm(false);
        },
      },
    );
  }

  const columns = buildColumns(handleAction);

  if (isLoading) return <ReferralsListSkeleton />;

  const patientName = patient ? `${patient.first_name} ${patient.last_name}` : "Paciente";

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]" aria-label="Ruta de navegación">
        <Link href="/patients" className="hover:text-foreground transition-colors">Pacientes</Link>
        <ChevronRight className="h-4 w-4" />
        <Link href={`/patients/${patientId}`} className="hover:text-foreground transition-colors">{patientName}</Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Referencias</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Referencias</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Referencias internas entre doctores de la clínica.
          </p>
        </div>
        <Button onClick={() => setShowCreateForm((p) => !p)}>
          <UserPlus className="mr-2 h-4 w-4" />
          Nueva referencia
        </Button>
      </div>

      {/* Create form */}
      {showCreateForm && (
        <form onSubmit={handleCreate} className="rounded-xl border border-[hsl(var(--border))] p-4 space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              type="text"
              value={toDoctorId}
              onChange={(e) => setToDoctorId(e.target.value)}
              placeholder="ID del doctor destino"
              className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-primary-600"
              required
            />
            <input
              type="text"
              value={specialty}
              onChange={(e) => setSpecialty(e.target.value)}
              placeholder="Especialidad (opcional)"
              className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-primary-600"
            />
          </div>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Motivo de la referencia..."
            rows={2}
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-transparent text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary-600"
            required
          />
          <div className="flex items-center gap-3">
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-primary-600"
            >
              <option value="low">Baja</option>
              <option value="normal">Normal</option>
              <option value="urgent">Urgente</option>
            </select>
            <div className="flex-1" />
            <Button type="button" variant="outline" size="sm" onClick={() => setShowCreateForm(false)}>Cancelar</Button>
            <Button type="submit" size="sm" disabled={createReferral.isPending}>
              {createReferral.isPending ? "Creando..." : "Crear referencia"}
            </Button>
          </div>
        </form>
      )}

      {/* Error state */}
      {isError ? (
        <EmptyState
          icon={AlertCircle}
          title="Error al cargar referencias"
          description="No se pudieron cargar las referencias. Intenta de nuevo."
        />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Sin referencias"
          description="No hay referencias para este paciente."
        />
      ) : (
        <>
          <DataTable<ReferralResponse>
            columns={columns}
            data={data.items}
            loading={isLoading}
            skeletonRows={4}
            rowKey="id"
            emptyMessage="No hay referencias."
          />
          {data.total > 20 && (
            <Pagination
              page={page}
              pageSize={20}
              total={data.total}
              onChange={setPage}
            />
          )}
        </>
      )}
    </div>
  );
}
