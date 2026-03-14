"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronRight,
  Edit,
  UserX,
  Phone,
  Mail,
  MapPin,
  AlertCircle,
  ShieldCheck,
  User,
  CalendarDays,
  Droplets,
  ClipboardList,
  FilePlus,
  Globe,
  FileText,
  Download,
  Bell,
  DollarSign,
  Share2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { EmptyState } from "@/components/empty-state";
import { MedicalHistoryTimeline } from "@/components/medical-history-timeline";
import { usePatient, useDeactivatePatient, useReactivatePatient, useManagePortalAccess } from "@/lib/hooks/use-patients";
import { useAuthStore } from "@/lib/hooks/use-auth";
import { usePatientReferralSummary } from "@/lib/hooks/use-referral-program";
import { useAppointments, type Appointment, type AppointmentStatus } from "@/lib/hooks/use-appointments";
import { useTreatmentPlans, type TreatmentPlanResponse } from "@/lib/hooks/use-treatment-plans";
import { useOrthoCases } from "@/lib/hooks/use-ortho";
import { OrthoStatusBadge } from "@/components/ortho/ortho-status-badge";
import { formatDate, formatDateTime, formatCurrency, getInitials } from "@/lib/utils";
import {
  DOCUMENT_TYPE_LABELS,
  GENDER_LABELS,
  REFERRAL_SOURCE_LABELS,
} from "@/lib/validations/patient";
import { VoiceSessionHistory } from "@/components/voice/voice-session-history";
import { RadiographAnalysisHistory } from "@/components/radiograph-analysis/radiograph-analysis-history";
import { RadiographAnalyzeButton } from "@/components/radiograph-analysis/radiograph-analyze-button";
import { ClinicalSummaryPanel } from "@/components/clinical-summary/clinical-summary-panel";

// ─── Appointment Status Config ────────────────────────────────────────────────

const APPOINTMENT_STATUS_CONFIG: Record<
  AppointmentStatus,
  { label: string; variant: "default" | "secondary" | "success" | "destructive" | "warning" }
> = {
  scheduled: { label: "Agendada", variant: "default" },
  confirmed: { label: "Confirmada", variant: "success" },
  in_progress: { label: "En curso", variant: "default" },
  completed: { label: "Completada", variant: "secondary" },
  cancelled: { label: "Cancelada", variant: "destructive" },
  no_show: { label: "No asistió", variant: "warning" },
};

const APPOINTMENT_TYPE_LABELS: Record<string, string> = {
  consultation: "Consulta",
  procedure: "Procedimiento",
  emergency: "Urgencia",
  follow_up: "Control",
};

const TREATMENT_STATUS_CONFIG: Record<string, { label: string; variant: "default" | "secondary" | "success" | "destructive" }> = {
  draft: { label: "Borrador", variant: "secondary" },
  active: { label: "Activo", variant: "default" },
  completed: { label: "Completado", variant: "success" },
  cancelled: { label: "Cancelado", variant: "destructive" },
};

const DOCUMENT_TYPE_MAP: Record<string, string> = {
  xray: "Radiografía",
  consent: "Consentimiento",
  lab_result: "Resultado de laboratorio",
  referral: "Remisión",
  photo: "Fotografía",
  other: "Otro",
};

// ─── Document types for inline hook ──────────────────────────────────────────

interface PatientDocument {
  id: string;
  patient_id: string;
  document_type: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  description: string | null;
  tooth_number: number | null;
  uploaded_by: string;
  download_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface PatientDocumentListResponse {
  items: PatientDocument[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Info Row ─────────────────────────────────────────────────────────────────

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[hsl(var(--muted))]">
        <Icon className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-[hsl(var(--muted-foreground))]">{label}</p>
        <p className="text-sm text-foreground mt-0.5">{value ?? "—"}</p>
      </div>
    </div>
  );
}

// ─── Tag List ─────────────────────────────────────────────────────────────────

function TagList({ items, emptyLabel }: { items: string[]; emptyLabel: string }) {
  if (!items || items.length === 0) {
    return <p className="text-sm text-[hsl(var(--muted-foreground))]">{emptyLabel}</p>;
  }
  return (
    <div className="flex flex-wrap gap-1.5 mt-1">
      {items.map((item) => (
        <Badge key={item} variant="outline" className="text-xs">
          {item}
        </Badge>
      ))}
    </div>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function PatientDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>
      {/* Header card */}
      <div className="flex items-start gap-4 p-6 border rounded-xl">
        <Skeleton className="h-16 w-16 rounded-full" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-5 w-16" />
        </div>
      </div>
      {/* Tabs skeleton */}
      <div className="space-y-4">
        <Skeleton className="h-9 w-full rounded-lg" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="p-4 border rounded-xl space-y-3">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Citas Tab Component ──────────────────────────────────────────────────────

function CitasTab({ patientId }: { patientId: string }) {
  const { data, isLoading } = useAppointments({ patient_id: patientId });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-4 p-4 border rounded-lg">
            <Skeleton className="h-10 w-10 rounded-md" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-32" />
            </div>
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  const appointments = data?.items ?? [];

  if (appointments.length === 0) {
    return (
      <EmptyState
        icon={CalendarDays}
        title="Sin citas registradas"
        description="Este paciente no tiene citas agendadas todavía."
        action={{ label: "Agendar cita", href: "/agenda" }}
      />
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {data?.total ?? appointments.length} cita{(data?.total ?? appointments.length) !== 1 ? "s" : ""}
        </p>
        <Button variant="outline" size="sm" asChild>
          <Link href="/agenda">
            <CalendarDays className="mr-1.5 h-3.5 w-3.5" />
            Ir a agenda
          </Link>
        </Button>
      </div>

      <div className="rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-[hsl(var(--muted))]">
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))]">Fecha</th>
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))]">Hora</th>
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))] hidden md:table-cell">Doctor</th>
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))] hidden sm:table-cell">Tipo</th>
              <th className="px-4 py-2.5 text-left font-medium text-[hsl(var(--muted-foreground))]">Estado</th>
            </tr>
          </thead>
          <tbody>
            {appointments.map((apt) => {
              const statusConfig = APPOINTMENT_STATUS_CONFIG[apt.status];
              const startDate = new Date(apt.start_time);
              const endDate = new Date(apt.end_time);
              return (
                <tr key={apt.id} className="border-b last:border-0 hover:bg-[hsl(var(--muted)/0.5)] transition-colors">
                  <td className="px-4 py-3">
                    {formatDate(startDate)}
                  </td>
                  <td className="px-4 py-3 text-[hsl(var(--muted-foreground))]">
                    {startDate.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}
                    {" - "}
                    {endDate.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    {apt.doctor_name ?? "—"}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell text-[hsl(var(--muted-foreground))]">
                    {APPOINTMENT_TYPE_LABELS[apt.type] ?? apt.type}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={statusConfig.variant} className="text-xs">
                      {statusConfig.label}
                    </Badge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Tratamientos Tab Component ──────────────────────────────────────────────

function TratamientosTab({ patientId }: { patientId: string }) {
  const { data, isLoading } = useTreatmentPlans(patientId, 1, 10);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {[1, 2].map((i) => (
          <div key={i} className="p-4 border rounded-xl space-y-3">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  const plans = data?.items ?? [];

  if (plans.length === 0) {
    return (
      <EmptyState
        icon={ClipboardList}
        title="Sin planes de tratamiento"
        description="Este paciente no tiene planes de tratamiento creados."
        action={{ label: "Crear plan", href: `/patients/${patientId}/treatment-plans/new` }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {data?.total ?? plans.length} plan{(data?.total ?? plans.length) !== 1 ? "es" : ""}
        </p>
        <Button size="sm" asChild>
          <Link href={`/patients/${patientId}/treatment-plans/new`}>
            <FilePlus className="mr-1.5 h-3.5 w-3.5" />
            Crear plan
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {plans.map((plan) => {
          const statusConfig = TREATMENT_STATUS_CONFIG[plan.status] ?? {
            label: plan.status,
            variant: "secondary" as const,
          };
          return (
            <Card key={plan.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-sm font-semibold truncate">
                    {plan.name}
                  </CardTitle>
                  <Badge variant={statusConfig.variant} className="text-xs shrink-0">
                    {statusConfig.label}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-[hsl(var(--muted-foreground))]">
                    <span>Progreso</span>
                    <span className="font-medium text-foreground">{plan.progress_percent}%</span>
                  </div>
                  <Progress value={plan.progress_percent} className="h-1.5" />
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-[hsl(var(--muted-foreground))]">
                    {plan.items.length} procedimiento{plan.items.length !== 1 ? "s" : ""}
                  </span>
                  <span className="font-semibold">
                    {formatCurrency(plan.total_cost_estimated)}
                  </span>
                </div>

                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Creado el {formatDate(plan.created_at)}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ─── Ortodoncia Tab Component ────────────────────────────────────────────────

function OrtodonciaTab({ patientId }: { patientId: string }) {
  const { data, isLoading } = useOrthoCases(patientId, 1, 10);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {[1, 2].map((i) => (
          <div key={i} className="p-4 border rounded-xl space-y-3">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-6 w-20 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  const cases = data?.items ?? [];

  if (cases.length === 0) {
    return (
      <EmptyState
        icon={ClipboardList}
        title="Sin casos de ortodoncia"
        description="Este paciente no tiene casos de ortodoncia creados."
        action={{ label: "Nuevo caso", href: `/patients/${patientId}/ortho/new` }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          {data?.total ?? cases.length} caso{(data?.total ?? cases.length) !== 1 ? "s" : ""}
        </p>
        <Button size="sm" asChild>
          <Link href={`/patients/${patientId}/ortho/new`}>
            <FilePlus className="mr-1.5 h-3.5 w-3.5" />
            Nuevo caso
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {cases.map((orthoCase) => (
          <Link key={orthoCase.id} href={`/patients/${patientId}/ortho/${orthoCase.id}`}>
            <Card className="hover:border-primary-600/30 transition-colors cursor-pointer">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-sm font-semibold truncate">
                    {orthoCase.case_number}
                  </CardTitle>
                  <OrthoStatusBadge status={orthoCase.status} />
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[hsl(var(--muted-foreground))]">
                    {ORTHO_APPLIANCE_LABELS[orthoCase.appliance_type] ?? orthoCase.appliance_type}
                  </span>
                  <span className="font-semibold">
                    {formatCurrency(orthoCase.total_cost_estimated)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-[hsl(var(--muted-foreground))]">
                  <span>{orthoCase.visit_count} visita{orthoCase.visit_count !== 1 ? "s" : ""}</span>
                  <span>Creado el {formatDate(orthoCase.created_at)}</span>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

const ORTHO_APPLIANCE_LABELS: Record<string, string> = {
  brackets: "Brackets",
  aligners: "Alineadores",
  mixed: "Mixto",
};

// ─── Documentos Tab Component ────────────────────────────────────────────────

function DocumentosTab({ patientId }: { patientId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["patient_documents", patientId],
    queryFn: () =>
      apiGet<PatientDocumentListResponse>(`/patients/${patientId}/documents?page=1&page_size=20`),
    enabled: Boolean(patientId),
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="flex items-center gap-4 p-4 border rounded-lg">
            <Skeleton className="h-10 w-10 rounded-md" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const documents = data?.items ?? [];

  if (documents.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="Sin documentos"
        description="Este paciente no tiene documentos subidos todavía."
      />
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        {data?.total ?? documents.length} documento{(data?.total ?? documents.length) !== 1 ? "s" : ""}
      </p>

      <div className="rounded-lg border divide-y">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center gap-4 px-4 py-3 hover:bg-[hsl(var(--muted)/0.5)] transition-colors"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-[hsl(var(--muted))]">
              <FileText className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{doc.file_name}</p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                {DOCUMENT_TYPE_MAP[doc.document_type] ?? doc.document_type}
                {" · "}
                {formatDate(doc.created_at)}
                {doc.description && ` · ${doc.description}`}
              </p>
            </div>
            {doc.document_type === "xray" && (
              <RadiographAnalyzeButton
                patientId={patientId}
                documentId={doc.id}
              />
            )}
            {doc.download_url && (
              <Button variant="ghost" size="sm" asChild>
                <a href={doc.download_url} target="_blank" rel="noopener noreferrer">
                  <Download className="h-4 w-4" />
                </a>
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Referral Summary Card ────────────────────────────────────────────────────

function ReferralSummaryCard({ patientId }: { patientId: string }) {
  const { data, isLoading } = usePatientReferralSummary(patientId);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-4 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Share2 className="h-4 w-4 text-primary-600" />
          Programa de referidos
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {data.referral_code ? (
          <>
            <div className="flex items-center gap-2">
              <code className="rounded bg-[hsl(var(--muted))] px-2 py-1 text-sm font-mono font-semibold tracking-wider">
                {data.referral_code}
              </code>
              <Badge variant={data.code_is_active ? "success" : "secondary"} className="text-xs">
                {data.code_is_active ? "Activo" : "Inactivo"}
              </Badge>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <p className="text-lg font-bold">{data.uses_count}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Usos</p>
              </div>
              <div>
                <p className="text-lg font-bold">{data.rewards_pending}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Pendientes</p>
              </div>
              <div>
                <p className="text-lg font-bold">{data.rewards_applied}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">Aplicados</p>
              </div>
            </div>
          </>
        ) : (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Sin código de referido generado.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PatientDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [showDeactivateDialog, setShowDeactivateDialog] = React.useState(false);

  const user = useAuthStore((s) => s.user);
  const isOwner = user?.role === "clinic_owner";
  const { data: patient, isLoading, isError } = usePatient(params.id, isOwner);
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivatePatient();
  const { mutate: reactivate, isPending: isReactivating } = useReactivatePatient();
  const { mutate: managePortal, isPending: isManagingPortal } = useManagePortalAccess();

  function handleDeactivate() {
    deactivate(params.id, {
      onSuccess: () => {
        setShowDeactivateDialog(false);
        // Refresh the current page to show updated state
        router.refresh();
      },
    });
  }

  if (isLoading) {
    return <PatientDetailSkeleton />;
  }

  if (isError || !patient) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Paciente no encontrado"
        description="El paciente que buscas no existe o no tienes permiso para verlo."
        action={{ label: "Volver a pacientes", href: "/patients" }}
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
          <Link href="/patients" className="hover:text-foreground transition-colors">
            Pacientes
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground font-medium truncate max-w-[200px]">
            {patient.full_name}
          </span>
        </nav>

        {/* ─── Patient Header ──────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between rounded-xl border border-[hsl(var(--border))] p-6 bg-[hsl(var(--card))]">
          <div className="flex items-start gap-4">
            <Avatar className="h-16 w-16 shrink-0">
              <AvatarFallback className="text-xl font-bold">{getInitials(patient.full_name)}</AvatarFallback>
            </Avatar>
            <div className="min-w-0 space-y-1">
              <h1 className="text-xl font-bold text-foreground truncate">{patient.full_name}</h1>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                <span className="font-medium">
                  {DOCUMENT_TYPE_LABELS[patient.document_type as keyof typeof DOCUMENT_TYPE_LABELS] ??
                    patient.document_type}
                </span>{" "}
                {patient.document_number}
              </p>
              {patient.is_active ? (
                <Badge variant="success">Activo</Badge>
              ) : (
                <Badge variant="secondary">Inactivo</Badge>
              )}
            </div>
          </div>

          <div className="flex flex-row gap-2 sm:flex-col sm:items-end md:flex-row flex-wrap">
            <Button variant="outline" size="sm" asChild>
              <Link href={`/patients/${patient.id}/edit`}>
                <Edit className="mr-1.5 h-3.5 w-3.5" />
                Editar
              </Link>
            </Button>
            {/* Quick-action buttons */}
            {patient.phone && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(`tel:${patient.phone}`, "_self")}
                title="Llamar paciente"
              >
                <Phone className="h-3.5 w-3.5" />
              </Button>
            )}
            <Button variant="outline" size="sm" asChild title="Ver balance">
              <Link href={`/patients/${patient.id}/invoices`}>
                <DollarSign className="h-3.5 w-3.5" />
              </Link>
            </Button>
            {patient.is_active && patient.portal_access && (
              <Badge variant="success" className="h-8 px-3 gap-1.5 text-xs">
                <Globe className="h-3 w-3" />
                Portal activo
              </Badge>
            )}
            {patient.is_active && !patient.portal_access && patient.email && (
              <Button
                variant="outline"
                size="sm"
                disabled={isManagingPortal}
                onClick={() =>
                  managePortal({
                    id: patient.id,
                    action: "grant",
                    invitation_channel: "email",
                  })
                }
              >
                <Globe className="mr-1.5 h-3.5 w-3.5" />
                {isManagingPortal ? "Enviando..." : "Dar acceso al portal"}
              </Button>
            )}
            {patient.is_active && patient.portal_access && (
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-[hsl(var(--muted-foreground))]"
                disabled={isManagingPortal}
                onClick={() =>
                  managePortal({ id: patient.id, action: "revoke" })
                }
              >
                {isManagingPortal ? "Revocando..." : "Revocar portal"}
              </Button>
            )}
            {patient.is_active && isOwner && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeactivateDialog(true)}
              >
                <UserX className="mr-1.5 h-3.5 w-3.5" />
                Desactivar
              </Button>
            )}
            {!patient.is_active && isOwner && (
              <Button
                variant="outline"
                size="sm"
                className="border-green-500 text-green-600 hover:bg-green-50 dark:hover:bg-green-950"
                disabled={isReactivating}
                onClick={() => reactivate(patient.id)}
              >
                <User className="mr-1.5 h-3.5 w-3.5" />
                {isReactivating ? "Reactivando..." : "Reactivar"}
              </Button>
            )}
          </div>
        </div>

        {/* ─── Tabs ────────────────────────────────────────────────────────── */}
        <Tabs defaultValue="resumen">
          <TabsList className="w-full sm:w-auto flex-wrap h-auto gap-1">
            <TabsTrigger value="resumen">Resumen</TabsTrigger>
            <TabsTrigger value="odontograma">Odontograma</TabsTrigger>
            <TabsTrigger value="periodontal">Periodontal</TabsTrigger>
            <TabsTrigger value="historial">Historial clinico</TabsTrigger>
            <TabsTrigger value="tratamientos">Tratamientos</TabsTrigger>
            <TabsTrigger value="ortodoncia">Ortodoncia</TabsTrigger>
            <TabsTrigger value="estetica-facial">Estética Facial</TabsTrigger>
            <TabsTrigger value="cotizaciones">Cotizaciones</TabsTrigger>
            <TabsTrigger value="recetas">Recetas</TabsTrigger>
            <TabsTrigger value="consentimientos">Consentimientos</TabsTrigger>
            <TabsTrigger value="facturas">Facturas</TabsTrigger>
            <TabsTrigger value="membresia">Membresía</TabsTrigger>
            <TabsTrigger value="familia">Familia</TabsTrigger>
            <TabsTrigger value="mensajes">Mensajes</TabsTrigger>
            <TabsTrigger value="referencias">Referencias</TabsTrigger>
            <TabsTrigger value="citas">Citas</TabsTrigger>
            <TabsTrigger value="voz">Voz</TabsTrigger>
            <TabsTrigger value="radiografia-ia">Radiografía IA</TabsTrigger>
            <TabsTrigger value="documentos">Documentos</TabsTrigger>
          </TabsList>

          {/* ── Resumen Tab ─────────────────────────────────────────────── */}
          <TabsContent value="resumen" className="mt-4">
            {/* AI Clinical Summary — shown first so doctors get instant context */}
            <Card className="mb-4">
              <CardContent className="pt-4">
                <ClinicalSummaryPanel patientId={patient.id} />
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Personal */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <User className="h-4 w-4 text-primary-600" />
                    Información personal
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <InfoRow
                    icon={CalendarDays}
                    label="Fecha de nacimiento"
                    value={patient.birthdate ? formatDate(patient.birthdate) : undefined}
                  />
                  <InfoRow
                    icon={User}
                    label="Género"
                    value={
                      patient.gender
                        ? GENDER_LABELS[patient.gender as keyof typeof GENDER_LABELS] ?? patient.gender
                        : undefined
                    }
                  />
                  <InfoRow
                    icon={Droplets}
                    label="Tipo de sangre"
                    value={patient.blood_type}
                  />
                </CardContent>
              </Card>

              {/* Contact */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Phone className="h-4 w-4 text-primary-600" />
                    Contacto
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <InfoRow icon={Phone} label="Teléfono principal" value={patient.phone} />
                  <InfoRow
                    icon={Phone}
                    label="Teléfono secundario"
                    value={patient.phone_secondary}
                  />
                  <InfoRow icon={Mail} label="Correo electrónico" value={patient.email} />
                  <InfoRow
                    icon={MapPin}
                    label="Dirección"
                    value={
                      patient.address
                        ? `${patient.address}${patient.city ? `, ${patient.city}` : ""}${patient.state_province ? `, ${patient.state_province}` : ""}`
                        : undefined
                    }
                  />
                </CardContent>
              </Card>

              {/* Emergency Contact */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-primary-600" />
                    Contacto de emergencia
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <InfoRow
                    icon={User}
                    label="Nombre"
                    value={patient.emergency_contact_name}
                  />
                  <InfoRow
                    icon={Phone}
                    label="Teléfono"
                    value={patient.emergency_contact_phone}
                  />
                </CardContent>
              </Card>

              {/* Medical */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-primary-600" />
                      Información médica
                    </CardTitle>
                    <Button variant="ghost" size="sm" asChild className="h-7 text-xs">
                      <Link href={`/patients/${patient.id}/anamnesis`}>
                        Ver anamnesis
                      </Link>
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <InfoRow
                      icon={ShieldCheck}
                      label="Aseguradora / EPS"
                      value={patient.insurance_provider}
                    />
                    {patient.insurance_policy_number && (
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5 pl-10">
                        Póliza: {patient.insurance_policy_number}
                      </p>
                    )}
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
                      Alergias
                    </p>
                    <TagList items={patient.allergies} emptyLabel="Sin alergias registradas" />
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
                      Enfermedades crónicas
                    </p>
                    <TagList
                      items={patient.chronic_conditions}
                      emptyLabel="Sin condiciones registradas"
                    />
                  </div>

                  {patient.referral_source && (
                    <InfoRow
                      icon={User}
                      label="¿Cómo nos conoció?"
                      value={
                        REFERRAL_SOURCE_LABELS[
                          patient.referral_source as keyof typeof REFERRAL_SOURCE_LABELS
                        ] ?? patient.referral_source
                      }
                    />
                  )}
                </CardContent>
              </Card>

              {/* Referral Program */}
              <ReferralSummaryCard patientId={patient.id} />
            </div>

            {/* Notes */}
            {patient.notes && (
              <Card className="mt-4">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold">Notas adicionales</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-[hsl(var(--muted-foreground))] whitespace-pre-wrap">
                    {patient.notes}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Metadata */}
            <Card className="mt-4">
              <CardContent className="pt-4">
                <div className="flex flex-col gap-1 sm:flex-row sm:gap-6 text-xs text-[hsl(var(--muted-foreground))]">
                  <span>
                    Registrado el{" "}
                    <span className="font-medium text-foreground">
                      {formatDateTime(patient.created_at)}
                    </span>
                  </span>
                  <Separator orientation="vertical" className="hidden sm:block h-4" />
                  <span>
                    Última actualización{" "}
                    <span className="font-medium text-foreground">
                      {formatDateTime(patient.updated_at)}
                    </span>
                  </span>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Odontograma Tab ──────────────────────────────────────────── */}
          <TabsContent value="odontograma" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Visualiza y edita el estado dental del paciente.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/odontogram`}>
                  Abrir Odontograma
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Periodontal Tab ──────────────────────────────────────────── */}
          <TabsContent value="periodontal" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Registros de medición de bolsas periodontales y parámetros clínicos.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/periodontal`}>
                  Abrir Periodontograma
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Historial Tab ────────────────────────────────────────────── */}
          <TabsContent value="historial" className="mt-4 space-y-4">
            {/* Action bar */}
            <div className="flex items-center justify-between">
              <Button variant="outline" size="sm" asChild>
                <Link href={`/patients/${patient.id}/clinical-records`}>
                  <ClipboardList className="mr-1.5 h-3.5 w-3.5" />
                  Ver todos
                </Link>
              </Button>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/patients/${patient.id}/anamnesis`}>
                    Anamnesis
                  </Link>
                </Button>
                <Button size="sm" asChild>
                  <Link href={`/patients/${patient.id}/clinical-records/new`}>
                    <FilePlus className="mr-1.5 h-3.5 w-3.5" />
                    Nueva nota clínica
                  </Link>
                </Button>
              </div>
            </div>

            <MedicalHistoryTimeline patientId={patient.id} />
          </TabsContent>

          {/* ── Tratamientos Tab ─────────────────────────────────────────── */}
          <TabsContent value="tratamientos" className="mt-4">
            <TratamientosTab patientId={patient.id} />
          </TabsContent>

          {/* ── Ortodoncia Tab ─────────────────────────────────────────── */}
          <TabsContent value="ortodoncia" className="mt-4">
            <OrtodonciaTab patientId={patient.id} />
          </TabsContent>

          {/* ── Estética Facial Tab ────────────────────────────────────── */}
          <TabsContent value="estetica-facial" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Registro de inyecciones y seguimiento de sesiones de estética facial.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/facial-aesthetics`}>
                  Abrir Estética Facial
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Cotizaciones Tab ─────────────────────────────────────────── */}
          <TabsContent value="cotizaciones" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Cotizaciones y presupuestos del paciente.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/quotations`}>
                  Ver Cotizaciones
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Recetas Tab ───────────────────────────────────────────────── */}
          <TabsContent value="recetas" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Prescripciones médicas del paciente.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/prescriptions`}>
                  Ver Recetas
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Consentimientos Tab ───────────────────────────────────────── */}
          <TabsContent value="consentimientos" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Consentimientos informados del paciente.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/consents`}>
                  Ver Consentimientos
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Facturas Tab ─────────────────────────────────────────────── */}
          <TabsContent value="facturas" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Facturas y pagos del paciente.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/invoices`}>
                  Ver Facturas
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Membresía Tab ────────────────────────────────────────────── */}
          <TabsContent value="membresia" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Plan de membresía y beneficios del paciente.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/membership`}>
                  Ver Membresía
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Familia Tab ──────────────────────────────────────────────── */}
          <TabsContent value="familia" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Grupo familiar y facturación consolidada.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/family`}>
                  Ver Grupo Familiar
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Mensajes Tab ─────────────────────────────────────────────── */}
          <TabsContent value="mensajes" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Conversaciones y mensajes con el paciente.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/messages`}>
                  Ver Mensajes
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Referencias Tab ──────────────────────────────────────────── */}
          <TabsContent value="referencias" className="mt-4">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Referencias a especialistas y seguimiento.
              </p>
              <Button asChild>
                <Link href={`/patients/${patient.id}/referrals`}>
                  Ver Referencias
                </Link>
              </Button>
            </div>
          </TabsContent>

          {/* ── Citas Tab ────────────────────────────────────────────────── */}
          <TabsContent value="citas" className="mt-4">
            <CitasTab patientId={patient.id} />
          </TabsContent>

          {/* ── Voz Tab ──────────────────────────────────────────────────── */}
          <TabsContent value="voz" className="mt-4">
            <VoiceSessionHistory patientId={patient.id} />
          </TabsContent>

          {/* ── Radiografía IA Tab ─────────────────────────────────────── */}
          <TabsContent value="radiografia-ia" className="mt-4">
            <RadiographAnalysisHistory patientId={patient.id} />
          </TabsContent>

          {/* ── Documentos Tab ───────────────────────────────────────────── */}
          <TabsContent value="documentos" className="mt-4">
            <DocumentosTab patientId={patient.id} />
          </TabsContent>
        </Tabs>
      </div>

      {/* ─── Deactivate Confirmation Dialog ──────────────────────────────── */}
      <Dialog open={showDeactivateDialog} onOpenChange={setShowDeactivateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Desactivar paciente</DialogTitle>
            <DialogDescription>
              ¿Estás seguro de que deseas desactivar a{" "}
              <span className="font-semibold text-foreground">{patient.full_name}</span>? El paciente
              no aparecerá en las búsquedas pero su historial clínico se conservará.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col-reverse sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setShowDeactivateDialog(false)}
              disabled={isDeactivating}
            >
              Cancelar
            </Button>
            <Button variant="destructive" onClick={handleDeactivate} disabled={isDeactivating}>
              {isDeactivating ? "Desactivando..." : "Desactivar paciente"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
