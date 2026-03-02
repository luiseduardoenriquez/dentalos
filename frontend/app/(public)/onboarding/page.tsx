"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import {
  ArrowRight,
  ArrowLeft,
  Building2,
  Clock,
  Users,
  PartyPopper,
  CheckCircle2,
  Upload,
  UserPlus,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

// ─── Step config ──────────────────────────────────────────────────────────────

const STEPS = [
  { id: 1, label: "Clínica", icon: Building2 },
  { id: 2, label: "Horarios", icon: Clock },
  { id: 3, label: "Equipo", icon: Users },
  { id: 4, label: "Listo", icon: CheckCircle2 },
] as const;

// ─── Step Progress Bar ────────────────────────────────────────────────────────

interface StepProgressProps {
  currentStep: number;
}

function StepProgress({ currentStep }: StepProgressProps) {
  return (
    <div className="mb-8">
      {/* Mobile: simple text indicator */}
      <p className="text-xs text-muted-foreground text-center mb-3 sm:hidden">
        Paso {currentStep} de {STEPS.length}
      </p>

      {/* Desktop: step circles */}
      <div className="hidden sm:flex items-center justify-center gap-0">
        {STEPS.map((step, idx) => {
          const StepIcon = step.icon;
          const isCompleted = step.id < currentStep;
          const isActive = step.id === currentStep;

          return (
            <div key={step.id} className="flex items-center">
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={cn(
                    "w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all",
                    isCompleted && "bg-primary-600 border-primary-600 text-white",
                    isActive && "bg-white dark:bg-zinc-900 border-primary-600 text-primary-600 shadow-sm",
                    !isCompleted && !isActive && "bg-white dark:bg-zinc-900 border-slate-200 dark:border-zinc-700 text-slate-300 dark:text-zinc-600",
                  )}
                  aria-current={isActive ? "step" : undefined}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <StepIcon className="h-4 w-4" aria-hidden="true" />
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium",
                    isActive ? "text-primary-600" : "text-muted-foreground",
                  )}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector */}
              {idx < STEPS.length - 1 && (
                <div
                  className={cn(
                    "w-16 h-px mx-1 mb-5 transition-colors",
                    step.id < currentStep
                      ? "bg-primary-600"
                      : "bg-slate-200 dark:bg-zinc-700",
                  )}
                  aria-hidden="true"
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Progress bar (mobile) */}
      <div className="sm:hidden w-full bg-slate-200 dark:bg-zinc-700 rounded-full h-1.5 mt-1">
        <div
          className="bg-primary-600 h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${((currentStep - 1) / (STEPS.length - 1)) * 100}%` }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}

// ─── Step 1: Clinic info ───────────────────────────────────────────────────────

function StepClinica({ onNext, isSaving }: { onNext: (data: { address: string; phone: string }) => void; isSaving: boolean }) {
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");

  function handleSubmit() {
    onNext({ address, phone });
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Información de la clínica</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Agrega los datos de tu clínica. Podrás editarlos después en Configuración.
        </p>
      </div>

      {/* Address */}
      <div className="space-y-1.5">
        <Label htmlFor="address">Dirección</Label>
        <Input
          id="address"
          type="text"
          placeholder="Calle 123 #45-67, Bogotá"
          autoComplete="street-address"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
      </div>

      {/* Phone */}
      <div className="space-y-1.5">
        <Label htmlFor="clinic_phone">Teléfono de la clínica</Label>
        <Input
          id="clinic_phone"
          type="tel"
          placeholder="+57 1 234 5678"
          autoComplete="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
      </div>

      {/* Logo upload placeholder */}
      <div className="space-y-1.5">
        <Label>Logo de la clínica</Label>
        <div className="flex items-center justify-center w-full h-32 rounded-lg border-2 border-dashed border-[hsl(var(--border))] bg-[hsl(var(--muted))/50] hover:border-primary-400 transition-colors cursor-pointer group">
          <div className="flex flex-col items-center gap-2 text-muted-foreground group-hover:text-primary-600 transition-colors">
            <Upload className="h-7 w-7" aria-hidden="true" />
            <div className="text-center">
              <p className="text-sm font-medium">Haz clic para subir tu logo</p>
              <p className="text-xs">PNG, JPG hasta 10 MB</p>
            </div>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">Opcional — puedes agregarlo después.</p>
      </div>

      <Button type="button" className="w-full" onClick={handleSubmit} disabled={isSaving}>
        {isSaving ? "Guardando..." : "Siguiente"}
        {!isSaving && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
      </Button>
    </div>
  );
}

// ─── Step 2: Horarios (placeholder) ──────────────────────────────────────────

function StepHorarios({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Horarios de atención</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configura cuándo está disponible tu clínica.
        </p>
      </div>

      {/* Placeholder */}
      <div className="flex flex-col items-center justify-center gap-3 py-10 rounded-lg border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--muted))/30]">
        <Clock className="h-10 w-10 text-muted-foreground/50" aria-hidden="true" />
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">Próximamente</p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xs">
            La configuración de horarios por día y doctor estará disponible en la próxima
            versión. Por ahora, configúralos desde el módulo de Agenda.
          </p>
        </div>
      </div>

      <div className="flex gap-3">
        <Button type="button" variant="outline" className="flex-1" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Atrás
        </Button>
        <Button type="button" className="flex-1" onClick={onNext}>
          Siguiente
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

// ─── Step 3: Team (placeholder) ───────────────────────────────────────────────

function StepEquipo({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Tu equipo</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Invita a tus colaboradores para que accedan a DentalOS.
        </p>
      </div>

      {/* Info callout */}
      <div className="flex gap-3 p-4 rounded-lg bg-primary-50 border border-primary-200 dark:bg-primary-900/20 dark:border-primary-800">
        <UserPlus className="h-5 w-5 text-primary-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium text-primary-700 dark:text-primary-300">
            Puedes invitar a tu equipo en cualquier momento
          </p>
          <p className="text-xs text-primary-600/80 dark:text-primary-400 mt-0.5">
            Ve a{" "}
            <strong>Configuración &rsaquo; Usuarios</strong> para invitar a doctores,
            asistentes y recepcionistas. Recibirán un enlace por correo para crear su cuenta.
          </p>
        </div>
      </div>

      {/* Placeholder invite form */}
      <div className="rounded-lg border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--muted))/30] p-5">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
          Vista previa — disponible próximamente
        </p>
        <div className="flex gap-2 opacity-40 pointer-events-none select-none" aria-hidden="true">
          <Input placeholder="correo@clinica.com" className="flex-1" disabled />
          <select
            disabled
            className="h-10 px-3 rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))] text-sm text-foreground"
          >
            <option>Doctor</option>
            <option>Asistente</option>
            <option>Recepcionista</option>
          </select>
          <Button type="button" size="sm" disabled variant="outline">
            Invitar
          </Button>
        </div>
      </div>

      <div className="flex gap-3">
        <Button type="button" variant="outline" className="flex-1" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Atrás
        </Button>
        <Button type="button" className="flex-1" onClick={onNext}>
          Continuar
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

// ─── Step 4: Success ──────────────────────────────────────────────────────────

function StepListo({ onFinish }: { onFinish: () => void }) {
  return (
    <div className="flex flex-col items-center text-center gap-5 py-4">
      <div className="relative">
        <div className="w-20 h-20 rounded-full bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center">
          <PartyPopper className="h-10 w-10 text-primary-600" aria-hidden="true" />
        </div>
        {/* Decorative ring */}
        <div
          className="absolute -inset-2 rounded-full border-2 border-primary-200 dark:border-primary-800 animate-pulse"
          aria-hidden="true"
        />
      </div>

      <div>
        <h2 className="text-xl font-semibold text-foreground">¡Todo listo!</h2>
        <p className="mt-2 text-sm text-muted-foreground max-w-xs leading-relaxed">
          Tu clínica está configurada y lista para empezar. Registra tu primer paciente y
          comienza a usar DentalOS.
        </p>
      </div>

      {/* Feature highlights */}
      <ul className="w-full space-y-2 text-sm">
        {[
          "Odontograma digital interactivo",
          "Registros clínicos electrónicos",
          "Agenda inteligente",
          "Facturación y consentimientos",
        ].map((feature) => (
          <li
            key={feature}
            className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg bg-[hsl(var(--muted))/40]"
          >
            <CheckCircle2 className="h-4 w-4 text-success-600 flex-shrink-0" aria-hidden="true" />
            <span className="text-foreground">{feature}</span>
          </li>
        ))}
      </ul>

      <Button type="button" className="w-full" size="lg" onClick={onFinish}>
        Ir al panel
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);

  const onboardingMutation = useMutation({
    mutationFn: (data: { step: number; data: Record<string, unknown> }) =>
      apiPost<{ current_step: number; completed: boolean; message: string }>("/onboarding", data),
  });

  const handleStep1Next = useCallback(
    (data: { address: string; phone: string }) => {
      onboardingMutation.mutate(
        { step: 0, data: { address: data.address, phone: data.phone } },
        {
          onSuccess: () => setStep(2),
        },
      );
    },
    [onboardingMutation],
  );

  function goNext() {
    setStep((s) => Math.min(s + 1, STEPS.length));
  }

  function goBack() {
    setStep((s) => Math.max(s - 1, 1));
  }

  function finish() {
    router.replace("/dashboard");
  }

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
      <StepProgress currentStep={step} />

      {step === 1 && <StepClinica onNext={handleStep1Next} isSaving={onboardingMutation.isPending} />}
      {step === 2 && <StepHorarios onNext={goNext} onBack={goBack} />}
      {step === 3 && <StepEquipo onNext={goNext} onBack={goBack} />}
      {step === 4 && <StepListo onFinish={finish} />}

      {onboardingMutation.isError && (
        <p className="mt-3 text-sm text-destructive text-center">
          No se pudo guardar. Inténtalo de nuevo.
        </p>
      )}
    </div>
  );
}
