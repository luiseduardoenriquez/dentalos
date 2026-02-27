"use client";

/**
 * Admin login page — multi-step: credentials → optional TOTP.
 *
 * Step 1: Email + password. POST /admin/auth/login.
 *   - If response.requires_totp = true → show step 2.
 *   - If response.access_token present → auth complete, redirect to /admin/dashboard.
 *
 * Step 2: 6-digit TOTP code. POST /admin/auth/login again with totp_code.
 *   - On success → auth complete, redirect to /admin/dashboard.
 *   - On failure → show "Código TOTP inválido" error.
 *
 * Credentials are retained in state across both steps so the second call
 * can include email + password + totp_code without asking the user to re-enter.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { AxiosError } from "axios";
import { ShieldCheck, KeyRound, ArrowLeft, Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { setAdminToken, useAdminAuthStore } from "@/lib/hooks/use-admin-auth";
import {
  useAdminLogin,
  type AdminLoginResponse,
} from "@/lib/hooks/use-admin";

// ─── Validation Schemas ────────────────────────────────────────────────────────

const credentialsSchema = z.object({
  email: z
    .string()
    .min(1, "El correo es requerido")
    .email("Correo inválido"),
  password: z
    .string()
    .min(1, "La contraseña es requerida"),
});

const totpSchema = z.object({
  totp_code: z
    .string()
    .length(6, "El código debe tener 6 dígitos")
    .regex(/^\d{6}$/, "Solo dígitos numéricos"),
});

type CredentialsForm = z.infer<typeof credentialsSchema>;
type TOTPForm = z.infer<typeof totpSchema>;

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Maps HTTP error status codes to user-facing Spanish messages.
 */
function getErrorMessage(error: unknown): string {
  const axiosError = error as AxiosError<{ message?: string; detail?: string }>;
  const status = axiosError?.response?.status;

  if (status === 401) {
    return "Credenciales inválidas. Verifica tu correo y contraseña.";
  }
  if (status === 429) {
    // Backend may include retry_after_seconds in response
    const detail = axiosError?.response?.data?.detail ?? "";
    const match = /(\d+)/.exec(String(detail));
    const minutes = match ? Math.ceil(Number(match[1]) / 60) : null;
    return minutes
      ? `Demasiados intentos. Intenta en ${minutes} minuto${minutes !== 1 ? "s" : ""}.`
      : "Demasiados intentos. Espera unos minutos antes de intentar nuevamente.";
  }
  if (status && status >= 500) {
    return "Error del servidor. Intenta nuevamente en unos momentos.";
  }
  return "Ocurrió un error inesperado. Intenta nuevamente.";
}

function getTOTPErrorMessage(error: unknown): string {
  const axiosError = error as AxiosError;
  const status = axiosError?.response?.status;

  if (status === 401) {
    return "Código TOTP inválido. Verifica el código en tu aplicación autenticadora.";
  }
  if (status === 429) {
    const detail = (axiosError?.response?.data as Record<string, unknown>)?.detail ?? "";
    const match = /(\d+)/.exec(String(detail));
    const minutes = match ? Math.ceil(Number(match[1]) / 60) : null;
    return minutes
      ? `Demasiados intentos. Intenta en ${minutes} minuto${minutes !== 1 ? "s" : ""}.`
      : "Demasiados intentos. Espera unos minutos antes de intentar nuevamente.";
  }
  return "Error al verificar el código. Intenta nuevamente.";
}

// ─── Step 1: Credentials ──────────────────────────────────────────────────────

interface CredentialsStepProps {
  onTOTPRequired: (email: string, password: string) => void;
}

function CredentialsStep({ onTOTPRequired }: CredentialsStepProps) {
  const router = useRouter();
  const set_admin_auth = useAdminAuthStore((s) => s.set_admin_auth);
  const { mutate: login, isPending, error } = useAdminLogin();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CredentialsForm>({
    resolver: zodResolver(credentialsSchema),
  });

  function onSubmit(values: CredentialsForm) {
    login(
      { email: values.email, password: values.password },
      {
        onSuccess: (data: AdminLoginResponse) => {
          if (data.requires_totp) {
            // Move to TOTP step — credentials are passed up to the parent
            onTOTPRequired(values.email, values.password);
            return;
          }
          // Direct login — TOTP not enabled or already verified
          if (data.access_token && data.admin_user) {
            setAdminToken(data.access_token);
            set_admin_auth(data.admin_user, data.admin_user.id);
            router.replace("/admin/dashboard");
          }
        },
      },
    );
  }

  const errorMessage = error ? getErrorMessage(error) : null;

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
      {/* Email */}
      <div className="space-y-1.5">
        <label
          htmlFor="email"
          className="block text-sm font-medium text-[hsl(var(--foreground))]"
        >
          Correo electrónico
        </label>
        <input
          {...register("email")}
          id="email"
          type="email"
          autoComplete="username"
          autoFocus
          placeholder="admin@dentalos.io"
          className={cn(
            "w-full rounded-lg border px-4 py-2.5 text-sm",
            "bg-[hsl(var(--background))] text-foreground placeholder:text-[hsl(var(--muted-foreground))]",
            "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
            "transition-colors duration-150",
            errors.email
              ? "border-destructive"
              : "border-[hsl(var(--border))]",
          )}
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? "email-error" : undefined}
        />
        {errors.email && (
          <p id="email-error" className="text-xs text-destructive" role="alert">
            {errors.email.message}
          </p>
        )}
      </div>

      {/* Password */}
      <div className="space-y-1.5">
        <label
          htmlFor="password"
          className="block text-sm font-medium text-[hsl(var(--foreground))]"
        >
          Contraseña
        </label>
        <div className="relative">
          <input
            {...register("password")}
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            placeholder="••••••••"
            className={cn(
              "w-full rounded-lg border px-4 py-2.5 pr-11 text-sm",
              "bg-[hsl(var(--background))] text-foreground placeholder:text-[hsl(var(--muted-foreground))]",
              "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
              "transition-colors duration-150",
              errors.password
                ? "border-destructive"
                : "border-[hsl(var(--border))]",
            )}
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? "password-error" : undefined}
          />
          <button
            type="button"
            onClick={() => setShowPassword((p) => !p)}
            className={cn(
              "absolute right-3 top-1/2 -translate-y-1/2",
              "text-[hsl(var(--muted-foreground))] hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded",
            )}
            aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        </div>
        {errors.password && (
          <p id="password-error" className="text-xs text-destructive" role="alert">
            {errors.password.message}
          </p>
        )}
      </div>

      {/* Server error */}
      {errorMessage && (
        <div
          className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3"
          role="alert"
        >
          <p className="text-sm text-destructive">{errorMessage}</p>
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={isPending}
        className={cn(
          "w-full rounded-lg px-4 py-2.5 text-sm font-semibold text-white",
          "bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2",
          "transition-colors duration-150",
          "disabled:opacity-60 disabled:cursor-not-allowed",
        )}
      >
        {isPending ? "Iniciando sesión..." : "Iniciar sesión"}
      </button>
    </form>
  );
}

// ─── Step 2: TOTP ─────────────────────────────────────────────────────────────

interface TOTPStepProps {
  email: string;
  password: string;
  onBack: () => void;
}

function TOTPStep({ email, password, onBack }: TOTPStepProps) {
  const router = useRouter();
  const set_admin_auth = useAdminAuthStore((s) => s.set_admin_auth);
  const { mutate: login, isPending, error } = useAdminLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<TOTPForm>({
    resolver: zodResolver(totpSchema),
  });

  function onSubmit(values: TOTPForm) {
    login(
      { email, password, totp_code: values.totp_code },
      {
        onSuccess: (data: AdminLoginResponse) => {
          if (!data.access_token || !data.admin_user) {
            // Backend returned success but without a token — should not happen
            setError("totp_code", { message: "Respuesta inesperada del servidor." });
            return;
          }
          setAdminToken(data.access_token);
          set_admin_auth(data.admin_user, data.admin_user.id);
          router.replace("/admin/dashboard");
        },
      },
    );
  }

  const errorMessage = error ? getTOTPErrorMessage(error) : null;

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
      {/* Back link */}
      <button
        type="button"
        onClick={onBack}
        className={cn(
          "flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]",
          "hover:text-foreground transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded",
        )}
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Volver
      </button>

      {/* Context text */}
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        Ingresa el código de 6 dígitos de tu aplicación autenticadora.
      </p>

      {/* TOTP input */}
      <div className="space-y-1.5">
        <label
          htmlFor="totp_code"
          className="block text-sm font-medium text-[hsl(var(--foreground))]"
        >
          Código de autenticación
        </label>
        <input
          {...register("totp_code")}
          id="totp_code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          autoFocus
          maxLength={6}
          placeholder="000000"
          className={cn(
            "w-full rounded-lg border px-4 py-2.5 text-sm text-center tracking-[0.4em] font-mono",
            "bg-[hsl(var(--background))] text-foreground placeholder:text-[hsl(var(--muted-foreground))] placeholder:tracking-normal",
            "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
            "transition-colors duration-150",
            errors.totp_code
              ? "border-destructive"
              : "border-[hsl(var(--border))]",
          )}
          aria-invalid={!!errors.totp_code}
          aria-describedby={errors.totp_code ? "totp-error" : undefined}
        />
        {errors.totp_code && (
          <p id="totp-error" className="text-xs text-destructive" role="alert">
            {errors.totp_code.message}
          </p>
        )}
      </div>

      {/* Server error */}
      {errorMessage && (
        <div
          className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3"
          role="alert"
        >
          <p className="text-sm text-destructive">{errorMessage}</p>
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={isPending}
        className={cn(
          "w-full rounded-lg px-4 py-2.5 text-sm font-semibold text-white",
          "bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2",
          "transition-colors duration-150",
          "disabled:opacity-60 disabled:cursor-not-allowed",
        )}
      >
        {isPending ? "Verificando..." : "Verificar código"}
      </button>
    </form>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Admin login page at /admin/login.
 *
 * This page is rendered OUTSIDE the (admin) layout so it does NOT go through
 * the auth guard — accessing it when unauthenticated is the intended flow.
 */
export default function AdminLoginPage() {
  // Step tracking and credential storage for the TOTP step
  const [step, setStep] = useState<"credentials" | "totp">("credentials");
  const [savedEmail, setSavedEmail] = useState("");
  const [savedPassword, setSavedPassword] = useState("");

  function handleTOTPRequired(email: string, password: string) {
    setSavedEmail(email);
    setSavedPassword(password);
    setStep("totp");
  }

  function handleBack() {
    setStep("credentials");
    // Do not clear saved email — UX: the email field will be pre-filled if
    // the user goes back, but React Hook Form reinitialises on remount so
    // the form starts fresh. That is acceptable for security.
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4 py-12">
      <div className="w-full max-w-sm">
        {/* Brand header */}
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 shadow-lg shadow-indigo-900/40">
            {step === "totp" ? (
              <KeyRound className="h-6 w-6 text-white" />
            ) : (
              <ShieldCheck className="h-6 w-6 text-white" />
            )}
          </div>
          <div className="text-center">
            <h1 className="text-xl font-bold text-white">
              Dental<span className="text-indigo-400">OS</span> Admin
            </h1>
            <p className="text-sm text-slate-400 mt-0.5">
              {step === "totp"
                ? "Verificación en dos pasos"
                : "Acceso restringido al personal autorizado"}
            </p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl shadow-black/40">
          {step === "credentials" ? (
            <CredentialsStep onTOTPRequired={handleTOTPRequired} />
          ) : (
            <TOTPStep
              email={savedEmail}
              password={savedPassword}
              onBack={handleBack}
            />
          )}
        </div>

        {/* Footer note */}
        <p className="mt-6 text-center text-xs text-slate-500">
          Acceso exclusivo para administradores de DentalOS.
          <br />
          Las sesiones expiran en 1 hora.
        </p>
      </div>
    </div>
  );
}
