"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ChevronLeft, AlertCircle, CheckCircle2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/empty-state";
import { ConsentPreview } from "@/components/consent-preview";
import { SignaturePad } from "@/components/signature-pad";
import { useConsent, useSignConsent } from "@/lib/hooks/use-consents";
import { usePatient } from "@/lib/hooks/use-patients";
import { useAuth } from "@/lib/hooks/use-auth";
import { cn } from "@/lib/utils";

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function SignPageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-9 w-32 rounded-md" />
      </div>
      <div className="space-y-3 rounded-lg border p-8">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
      <Skeleton className="h-44 w-full rounded-lg" />
      <Skeleton className="h-9 w-full rounded-md" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SignConsentPage() {
  const params = useParams<{ id: string; consentId: string }>();
  const router = useRouter();
  const patient_id = params.id;
  const consent_id = params.consentId;

  const [has_accepted, set_has_accepted] = React.useState(false);
  const [signature_base64, set_signature_base64] = React.useState<string | null>(null);
  const [is_signed, set_is_signed] = React.useState(false);

  const { data: patient, isLoading: is_loading_patient } = usePatient(patient_id);
  const {
    data: consent,
    isLoading: is_loading_consent,
    isError,
  } = useConsent(patient_id, consent_id);
  const { mutate: sign_consent, isPending: is_signing } = useSignConsent(
    patient_id,
    consent_id,
  );

  // Determine signer type from consent status:
  // draft → patient is the first signer
  // pending_signatures → doctor signs next
  const { has_permission } = useAuth();
  const is_doctor = has_permission("odontogram:write"); // proxy for doctor-level access
  const signer_type: "patient" | "doctor" =
    consent?.status === "pending_signatures" ? "doctor" : "patient";

  const is_loading = is_loading_patient || is_loading_consent;
  const can_submit = has_accepted && signature_base64 !== null;

  // Redirect away if consent is already signed or voided
  React.useEffect(() => {
    if (!consent) return;
    if (consent.status === "signed" || consent.status === "voided") {
      router.replace(`/patients/${patient_id}/consents/${consent_id}`);
    }
  }, [consent, patient_id, consent_id, router]);

  function handle_signature(base64: string) {
    set_signature_base64(base64);
  }

  function handle_clear() {
    set_signature_base64(null);
  }

  function handle_submit() {
    if (!can_submit || !signature_base64) return;

    sign_consent(
      { signature_base64, signer_type },
      {
        onSuccess: () => {
          set_is_signed(true);
          // Brief delay before redirecting to detail page
          setTimeout(() => {
            router.push(`/patients/${patient_id}/consents/${consent_id}`);
          }, 1500);
        },
      },
    );
  }

  if (is_loading) {
    return <SignPageSkeleton />;
  }

  if (isError || !consent) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Consentimiento no encontrado"
        description="El consentimiento que buscas no existe o no tienes permiso para acceder."
        action={{
          label: "Volver",
          href: `/patients/${patient_id}/consents`,
        }}
      />
    );
  }

  // ── Success State ───────────────────────────────────────────────────
  if (is_signed) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center space-y-4 py-16">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-success-50 dark:bg-success-700/20">
          <CheckCircle2 className="h-10 w-10 text-success-600 dark:text-success-400" />
        </div>
        <h2 className="text-xl font-bold text-foreground">Firma registrada</h2>
        <p className="text-sm text-[hsl(var(--muted-foreground))] max-w-sm">
          La firma fue registrada exitosamente. Redirigiendo al consentimiento...
        </p>
      </div>
    );
  }

  // ── Signing UI ──────────────────────────────────────────────────────
  return (
    <div className="space-y-6 pb-24">
      {/* ─── Back Link ───────────────────────────────────────────────── */}
      <div>
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/patients/${patient_id}/consents/${consent_id}`}>
            <ChevronLeft className="mr-1 h-4 w-4" />
            Volver al consentimiento
          </Link>
        </Button>
      </div>

      {/* ─── Page Title ──────────────────────────────────────────────── */}
      <div className="space-y-1">
        <h1 className="text-xl font-bold text-foreground">Firma de consentimiento</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Paciente:{" "}
          <span className="font-medium text-foreground">
            {patient?.full_name ?? "—"}
          </span>
          {signer_type === "doctor" && (
            <span className="ml-2 text-xs font-medium text-primary-600">
              (firma del doctor)
            </span>
          )}
        </p>
      </div>

      {/* ─── Consent Content (scrollable) ────────────────────────────── */}
      <div className="max-h-[50vh] overflow-y-auto rounded-lg border border-[hsl(var(--border))]">
        <ConsentPreview
          htmlContent={consent.content_rendered}
          status={consent.status}
          className="rounded-none border-none"
        />
      </div>

      {/* ─── Acceptance Checkbox ─────────────────────────────────────── */}
      <div
        className={cn(
          "flex items-start gap-3 rounded-lg border p-4",
          has_accepted
            ? "border-success-500/30 bg-success-50 dark:border-success-500/40 dark:bg-success-700/10"
            : "border-[hsl(var(--border))] bg-[hsl(var(--card))]",
          "transition-colors",
        )}
      >
        <Checkbox
          id="accept-terms"
          checked={has_accepted}
          onCheckedChange={(checked) => set_has_accepted(Boolean(checked))}
          disabled={is_signing}
          className="mt-0.5 shrink-0"
        />
        <label
          htmlFor="accept-terms"
          className="cursor-pointer text-sm leading-relaxed"
        >
          <span className="font-semibold text-foreground">He leído y acepto</span>{" "}
          <span className="text-[hsl(var(--muted-foreground))]">
            el contenido de este consentimiento informado. Entiendo los procedimientos,
            riesgos y beneficios descritos, y otorgo mi autorización de manera voluntaria.
          </span>
        </label>
      </div>

      {/* ─── Signature Pad ───────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary-600" />
            {signer_type === "doctor" ? "Firma del doctor" : "Firma del paciente"}
          </CardTitle>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Dibuja tu firma en el área de abajo usando el mouse o tu dedo.
          </p>
        </CardHeader>
        <CardContent>
          <SignaturePad
            onSignature={handle_signature}
            onClear={handle_clear}
            height={200}
            disabled={is_signing || !has_accepted}
          />
          {signature_base64 && (
            <p className="mt-2 flex items-center gap-1.5 text-xs text-success-600 dark:text-success-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Firma capturada. Lista para enviar.
            </p>
          )}
        </CardContent>
      </Card>

      {/* ─── Submit Button ───────────────────────────────────────────── */}
      <div className="sticky bottom-4 pt-2">
        <Button
          size="lg"
          className="w-full"
          onClick={handle_submit}
          disabled={!can_submit || is_signing}
        >
          {is_signing ? "Registrando firma..." : "Firmar Consentimiento"}
        </Button>
        {!has_accepted && (
          <p className="mt-2 text-center text-xs text-[hsl(var(--muted-foreground))]">
            Debes marcar "He leído y acepto" antes de firmar.
          </p>
        )}
        {has_accepted && !signature_base64 && (
          <p className="mt-2 text-center text-xs text-[hsl(var(--muted-foreground))]">
            Dibuja tu firma en el área de arriba para continuar.
          </p>
        )}
      </div>
    </div>
  );
}
