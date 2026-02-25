"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ChevronRight,
  AlertCircle,
  Download,
  PenLine,
  Ban,
  CalendarDays,
  Clock,
  UserX,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { EmptyState } from "@/components/empty-state";
import { ConsentStatusBadge } from "@/components/consent-status-badge";
import { ConsentPreview } from "@/components/consent-preview";
import { VoidConsentDialog } from "@/components/void-consent-dialog";
import { useConsent, useVoidConsent, useConsentPdf } from "@/lib/hooks/use-consents";
import { usePatient } from "@/lib/hooks/use-patients";
import { formatDateTime } from "@/lib/utils";

// ─── Category Labels ──────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  general: "General",
  surgery: "Cirugía",
  sedation: "Sedación",
  orthodontics: "Ortodoncia",
  implants: "Implantes",
  endodontics: "Endodoncia",
  pediatric: "Pediátrico",
};

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function ConsentDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-40" />
      </div>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-6 w-64" />
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-9 w-32 rounded-md" />
              <Skeleton className="h-9 w-24 rounded-md" />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-36" />
        </CardContent>
      </Card>
      <div className="space-y-3 rounded-lg border p-8">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ConsentDetailPage() {
  const params = useParams<{ id: string; consentId: string }>();
  const patient_id = params.id;
  const consent_id = params.consentId;

  const [void_dialog_open, set_void_dialog_open] = React.useState(false);

  const { data: patient, isLoading: is_loading_patient } = usePatient(patient_id);
  const {
    data: consent,
    isLoading: is_loading_consent,
    isError,
  } = useConsent(patient_id, consent_id);
  const { mutate: void_consent, isPending: is_voiding } = useVoidConsent(
    patient_id,
    consent_id,
  );

  // Only fetch PDF when consent is signed
  const should_fetch_pdf = consent?.status === "signed";
  const { data: pdf_url, isLoading: is_loading_pdf } = useConsentPdf(
    should_fetch_pdf ? patient_id : null,
    should_fetch_pdf ? consent_id : null,
  );

  const is_loading = is_loading_patient || is_loading_consent;

  function handle_void(reason: string) {
    void_consent(
      { reason },
      {
        onSuccess: () => {
          set_void_dialog_open(false);
        },
      },
    );
  }

  if (is_loading) {
    return <ConsentDetailSkeleton />;
  }

  if (isError || !consent) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Consentimiento no encontrado"
        description="El consentimiento que buscas no existe o no tienes permiso para verlo."
        action={{
          label: "Volver a consentimientos",
          href: `/patients/${patient_id}/consents`,
        }}
      />
    );
  }

  return (
    <>
      <div className="space-y-6">
        {/* ─── Breadcrumb ──────────────────────────────────────────── */}
        <nav
          className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
          aria-label="Ruta de navegación"
        >
          <Link href="/patients" className="hover:text-foreground transition-colors">
            Pacientes
          </Link>
          <ChevronRight className="h-4 w-4" />
          <Link
            href={`/patients/${patient_id}`}
            className="hover:text-foreground transition-colors truncate max-w-[120px]"
          >
            {patient?.full_name ?? "Paciente"}
          </Link>
          <ChevronRight className="h-4 w-4" />
          <Link
            href={`/patients/${patient_id}/consents`}
            className="hover:text-foreground transition-colors"
          >
            Consentimientos
          </Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground font-medium truncate max-w-[180px]">
            {consent.template_name}
          </span>
        </nav>

        {/* ─── Header Card ─────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              {/* Title + Status */}
              <div className="space-y-2 min-w-0">
                <h1 className="text-lg font-bold text-foreground">
                  {consent.template_name}
                </h1>
                <div className="flex items-center gap-2 flex-wrap">
                  <ConsentStatusBadge status={consent.status} />
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    {CATEGORY_LABELS[consent.category] ?? consent.category}
                  </span>
                </div>
              </div>

              {/* Action Buttons — conditionally rendered by status */}
              <div className="flex flex-wrap gap-2 shrink-0">
                {/* draft: Sign as patient */}
                {consent.status === "draft" && (
                  <Button asChild>
                    <Link href={`/patients/${patient_id}/consents/${consent_id}/sign`}>
                      <PenLine className="mr-1.5 h-4 w-4" />
                      Firmar
                    </Link>
                  </Button>
                )}

                {/* pending_signatures: Sign as doctor */}
                {consent.status === "pending_signatures" && (
                  <Button asChild>
                    <Link href={`/patients/${patient_id}/consents/${consent_id}/sign`}>
                      <PenLine className="mr-1.5 h-4 w-4" />
                      Firmar como Doctor
                    </Link>
                  </Button>
                )}

                {/* signed: Download PDF + Void */}
                {consent.status === "signed" && (
                  <>
                    {is_loading_pdf ? (
                      <Button variant="outline" disabled>
                        <Download className="mr-1.5 h-4 w-4" />
                        Preparando PDF...
                      </Button>
                    ) : pdf_url ? (
                      <Button variant="outline" asChild>
                        <a href={pdf_url} download={`consentimiento-${consent_id}.pdf`}>
                          <Download className="mr-1.5 h-4 w-4" />
                          Descargar PDF
                        </a>
                      </Button>
                    ) : null}
                    <Button
                      variant="destructive"
                      onClick={() => set_void_dialog_open(true)}
                    >
                      <Ban className="mr-1.5 h-4 w-4" />
                      Anular
                    </Button>
                  </>
                )}

                {/* voided: No actions — informational only */}
              </div>
            </div>
          </CardHeader>

          <CardContent>
            <div className="flex flex-col gap-2 sm:flex-row sm:gap-6 text-sm text-[hsl(var(--muted-foreground))]">
              <span className="flex items-center gap-1.5">
                <CalendarDays className="h-3.5 w-3.5" />
                Creado el{" "}
                <span className="font-medium text-foreground">
                  {formatDateTime(consent.created_at)}
                </span>
              </span>

              {consent.signed_at && (
                <>
                  <Separator orientation="vertical" className="hidden sm:block h-4" />
                  <span className="flex items-center gap-1.5">
                    <PenLine className="h-3.5 w-3.5" />
                    Firmado el{" "}
                    <span className="font-medium text-foreground">
                      {formatDateTime(consent.signed_at)}
                    </span>
                  </span>
                </>
              )}

              {consent.voided_at && (
                <>
                  <Separator orientation="vertical" className="hidden sm:block h-4" />
                  <span className="flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5" />
                    Anulado el{" "}
                    <span className="font-medium text-foreground">
                      {formatDateTime(consent.voided_at)}
                    </span>
                  </span>
                </>
              )}
            </div>

            {/* ─── Void Reason ───────────────────────────────────── */}
            {consent.status === "voided" && consent.void_reason && (
              <div className="mt-4 rounded-md border border-destructive-200 bg-destructive-50 p-4 dark:border-destructive-700/40 dark:bg-destructive-900/20">
                <div className="flex items-start gap-2">
                  <UserX className="mt-0.5 h-4 w-4 shrink-0 text-destructive-600 dark:text-destructive-400" />
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-destructive-700 dark:text-destructive-300">
                      Motivo de anulación
                    </p>
                    <p className="mt-1 text-sm text-destructive-600 dark:text-destructive-400">
                      {consent.void_reason}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ─── Consent Content ──────────────────────────────────────── */}
        <div>
          <CardTitle className="mb-3 text-sm font-semibold text-[hsl(var(--muted-foreground))]">
            Contenido del consentimiento
          </CardTitle>
          <ConsentPreview
            htmlContent={consent.content_rendered}
            status={consent.status}
          />
        </div>
      </div>

      {/* ─── Void Dialog ────────────────────────────────────────────── */}
      <VoidConsentDialog
        open={void_dialog_open}
        onOpenChange={set_void_dialog_open}
        onVoid={handle_void}
        isLoading={is_voiding}
      />
    </>
  );
}
