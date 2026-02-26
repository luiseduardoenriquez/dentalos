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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { usePatient, useDeactivatePatient } from "@/lib/hooks/use-patients";
import { formatDate, formatDateTime, getInitials } from "@/lib/utils";
import {
  DOCUMENT_TYPE_LABELS,
  GENDER_LABELS,
  REFERRAL_SOURCE_LABELS,
} from "@/lib/validations/patient";

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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PatientDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [showDeactivateDialog, setShowDeactivateDialog] = React.useState(false);

  const { data: patient, isLoading, isError } = usePatient(params.id);
  const { mutate: deactivate, isPending: isDeactivating } = useDeactivatePatient();

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

          <div className="flex flex-row gap-2 sm:flex-col sm:items-end md:flex-row">
            <Button variant="outline" size="sm" asChild>
              <Link href={`/patients/${patient.id}/edit`}>
                <Edit className="mr-1.5 h-3.5 w-3.5" />
                Editar
              </Link>
            </Button>
            {patient.is_active && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeactivateDialog(true)}
              >
                <UserX className="mr-1.5 h-3.5 w-3.5" />
                Desactivar
              </Button>
            )}
          </div>
        </div>

        {/* ─── Tabs ────────────────────────────────────────────────────────── */}
        <Tabs defaultValue="resumen">
          <TabsList className="w-full sm:w-auto">
            <TabsTrigger value="resumen">Resumen</TabsTrigger>
            <TabsTrigger value="odontograma">Odontograma</TabsTrigger>
            <TabsTrigger value="historial">Historial clinico</TabsTrigger>
            <TabsTrigger value="tratamientos">Tratamientos</TabsTrigger>
            <TabsTrigger value="citas">Citas</TabsTrigger>
            <TabsTrigger value="documentos">Documentos</TabsTrigger>
          </TabsList>

          {/* ── Resumen Tab ─────────────────────────────────────────────── */}
          <TabsContent value="resumen" className="mt-4">
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
            <EmptyState
              title="Planes de tratamiento"
              description="Próximamente podrás gestionar los planes de tratamiento del paciente aquí."
            />
          </TabsContent>

          {/* ── Citas Tab ────────────────────────────────────────────────── */}
          <TabsContent value="citas" className="mt-4">
            <EmptyState
              title="Citas"
              description="Próximamente podrás ver el historial de citas del paciente aquí."
            />
          </TabsContent>

          {/* ── Documentos Tab ───────────────────────────────────────────── */}
          <TabsContent value="documentos" className="mt-4">
            <EmptyState
              title="Documentos"
              description="Próximamente podrás subir y gestionar documentos del paciente aquí."
            />
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
