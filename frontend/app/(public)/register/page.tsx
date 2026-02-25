"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Loader2, ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/lib/hooks/use-toast";
import { useRegister } from "@/lib/hooks/use-register";
import {
  registerSchema,
  COUNTRY_LABELS,
  SUPPORTED_COUNTRIES,
  type RegisterFormValues,
} from "@/lib/validations/auth";
import { cn } from "@/lib/utils";

// ─── Step Indicator ───────────────────────────────────────────────────────────

const STEPS = [
  { label: "Tu cuenta", number: 1 },
  { label: "Tu clínica", number: 2 },
];

interface StepIndicatorProps {
  currentStep: number;
}

function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-0 mb-8" role="progressbar" aria-valuenow={currentStep} aria-valuemin={1} aria-valuemax={2} aria-label="Progreso de registro">
      {STEPS.map((step, idx) => {
        const isCompleted = step.number < currentStep;
        const isActive = step.number === currentStep;

        return (
          <div key={step.number} className="flex items-center flex-1">
            {/* Circle */}
            <div className="flex flex-col items-center gap-1 flex-shrink-0">
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium border-2 transition-colors",
                  isCompleted && "bg-primary-600 border-primary-600 text-white",
                  isActive && "bg-white dark:bg-zinc-900 border-primary-600 text-primary-600",
                  !isActive && !isCompleted && "bg-white dark:bg-zinc-900 border-slate-300 dark:border-zinc-600 text-slate-400",
                )}
                aria-current={isActive ? "step" : undefined}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                ) : (
                  step.number
                )}
              </div>
              <span
                className={cn(
                  "text-xs whitespace-nowrap",
                  isActive ? "text-primary-600 font-medium" : "text-muted-foreground",
                )}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line (not after last step) */}
            {idx < STEPS.length - 1 && (
              <div
                className={cn(
                  "flex-1 h-px mx-2 mb-5 transition-colors",
                  isCompleted ? "bg-primary-600" : "bg-slate-200 dark:bg-zinc-700",
                )}
                aria-hidden="true"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Password Strength Meter ──────────────────────────────────────────────────

function passwordStrength(pw: string): { score: number; label: string; color: string } {
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;

  if (score <= 2) return { score, label: "Débil", color: "bg-destructive-500" };
  if (score === 3) return { score, label: "Regular", color: "bg-accent-500" };
  return { score, label: "Fuerte", color: "bg-success-600" };
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RegisterPage() {
  const router = useRouter();
  const { error: toastError } = useToast();
  const [step, setStep] = useState(1);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    trigger,
    watch,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    mode: "onTouched",
  });

  const { mutate: doRegister, isPending } = useRegister();

  const passwordValue = watch("password") ?? "";
  const strength = passwordValue ? passwordStrength(passwordValue) : null;

  // Validate step 1 fields before proceeding to step 2
  async function handleNext() {
    const valid = await trigger(["name", "email", "password", "phone"]);
    if (valid) setStep(2);
  }

  function onSubmit(values: RegisterFormValues) {
    doRegister(values, {
      onSuccess: () => {
        router.replace("/onboarding");
      },
      onError: (err) => {
        const apiErr = err as { response?: { data?: { message?: string } } };
        toastError(
          "Error al crear la cuenta",
          apiErr.response?.data?.message ??
            "Inténtalo de nuevo o contacta soporte.",
        );
      },
    });
  }

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">Registrar clínica</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Crea tu cuenta y empieza a usar DentalOS gratis.
        </p>
      </div>

      <StepIndicator currentStep={step} />

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        {/* ── Step 1: Personal data ── */}
        {step === 1 && (
          <div className="space-y-5">
            {/* Full name */}
            <div className="space-y-1.5">
              <Label htmlFor="name" required>
                Nombre completo
              </Label>
              <Input
                id="name"
                type="text"
                autoComplete="name"
                placeholder="Dr. Juan García"
                aria-invalid={!!errors.name}
                aria-describedby={errors.name ? "name-error" : undefined}
                {...register("name")}
              />
              {errors.name && (
                <p id="name-error" className="text-xs text-destructive-600 dark:text-destructive-400">
                  {errors.name.message}
                </p>
              )}
            </div>

            {/* Email */}
            <div className="space-y-1.5">
              <Label htmlFor="email" required>
                Correo electrónico
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="doctor@miclínica.com"
                aria-invalid={!!errors.email}
                aria-describedby={errors.email ? "email-error" : undefined}
                {...register("email")}
              />
              {errors.email && (
                <p id="email-error" className="text-xs text-destructive-600 dark:text-destructive-400">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <Label htmlFor="password" required>
                Contraseña
              </Label>
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                placeholder="Mínimo 8 caracteres"
                aria-invalid={!!errors.password}
                aria-describedby={
                  errors.password
                    ? "password-error"
                    : strength
                      ? "password-strength"
                      : undefined
                }
                endAdornment={
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                    className="pointer-events-auto text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" aria-hidden="true" />
                    ) : (
                      <Eye className="h-4 w-4" aria-hidden="true" />
                    )}
                  </button>
                }
                {...register("password")}
              />
              {/* Strength meter */}
              {strength && !errors.password && (
                <div id="password-strength" aria-live="polite">
                  <div className="flex gap-1 mt-1.5">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className={cn(
                          "h-1 flex-1 rounded-full transition-colors",
                          i <= strength.score ? strength.color : "bg-slate-200 dark:bg-zinc-700",
                        )}
                        aria-hidden="true"
                      />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Seguridad:{" "}
                    <span
                      className={cn(
                        strength.score <= 2 && "text-destructive-600",
                        strength.score === 3 && "text-accent-600",
                        strength.score >= 4 && "text-success-600",
                      )}
                    >
                      {strength.label}
                    </span>
                  </p>
                </div>
              )}
              {errors.password && (
                <p id="password-error" className="text-xs text-destructive-600 dark:text-destructive-400">
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Phone (optional) */}
            <div className="space-y-1.5">
              <Label htmlFor="phone">
                Teléfono{" "}
                <span className="text-xs font-normal text-muted-foreground">(opcional)</span>
              </Label>
              <Input
                id="phone"
                type="tel"
                autoComplete="tel"
                placeholder="+573001234567"
                aria-invalid={!!errors.phone}
                aria-describedby={errors.phone ? "phone-error" : undefined}
                {...register("phone")}
              />
              {errors.phone && (
                <p id="phone-error" className="text-xs text-destructive-600 dark:text-destructive-400">
                  {errors.phone.message}
                </p>
              )}
            </div>

            <Button type="button" className="w-full" onClick={handleNext}>
              Siguiente
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        )}

        {/* ── Step 2: Clinic data ── */}
        {step === 2 && (
          <div className="space-y-5">
            {/* Clinic name */}
            <div className="space-y-1.5">
              <Label htmlFor="clinic_name" required>
                Nombre de la clínica
              </Label>
              <Input
                id="clinic_name"
                type="text"
                autoComplete="organization"
                placeholder="Clínica Dental García"
                aria-invalid={!!errors.clinic_name}
                aria-describedby={errors.clinic_name ? "clinic-name-error" : undefined}
                {...register("clinic_name")}
              />
              {errors.clinic_name && (
                <p id="clinic-name-error" className="text-xs text-destructive-600 dark:text-destructive-400">
                  {errors.clinic_name.message}
                </p>
              )}
            </div>

            {/* Country */}
            <div className="space-y-1.5">
              <Label htmlFor="country" required>
                País
              </Label>
              <div className="relative">
                <select
                  id="country"
                  aria-invalid={!!errors.country}
                  aria-describedby={errors.country ? "country-error" : undefined}
                  defaultValue=""
                  className={cn(
                    "flex h-10 w-full appearance-none rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                    "px-3 py-2 pr-8 text-sm text-foreground",
                    "transition-colors duration-150",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-0",
                    "disabled:cursor-not-allowed disabled:opacity-50",
                    errors.country && "border-destructive-500",
                  )}
                  {...register("country")}
                >
                  <option value="" disabled>
                    Selecciona un país
                  </option>
                  {SUPPORTED_COUNTRIES.map((code) => (
                    <option key={code} value={code}>
                      {COUNTRY_LABELS[code]}
                    </option>
                  ))}
                </select>
                {/* Custom chevron */}
                <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
              {errors.country && (
                <p id="country-error" className="text-xs text-destructive-600 dark:text-destructive-400">
                  {errors.country.message}
                </p>
              )}
            </div>

            {/* Terms notice */}
            <p className="text-xs text-muted-foreground leading-relaxed">
              Al crear tu cuenta aceptas nuestros{" "}
              <a href="#" className="text-primary-600 hover:underline dark:text-primary-400">
                Términos de servicio
              </a>{" "}
              y{" "}
              <a href="#" className="text-primary-600 hover:underline dark:text-primary-400">
                Política de privacidad
              </a>
              .
            </p>

            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                onClick={() => setStep(1)}
                disabled={isPending}
              >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                Atrás
              </Button>
              <Button type="submit" className="flex-1" disabled={isPending}>
                {isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Creando...
                  </>
                ) : (
                  "Crear cuenta"
                )}
              </Button>
            </div>
          </div>
        )}
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        ¿Ya tienes cuenta?{" "}
        <Link
          href="/login"
          className="font-medium text-primary-600 hover:underline dark:text-primary-400"
        >
          Iniciar sesión
        </Link>
      </p>
    </div>
  );
}
