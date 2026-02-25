"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Eye, EyeOff, Loader2, ArrowLeft, Mail } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/lib/hooks/use-toast";
import { apiPost } from "@/lib/api-client";
import { setAccessToken } from "@/lib/auth";
import { useAuthStore, type MeResponse } from "@/lib/hooks/use-auth";
import { acceptInviteSchema, type AcceptInviteFormValues } from "@/lib/validations/auth";

// ─── Response type ────────────────────────────────────────────────────────────

interface AcceptInviteResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  me: MeResponse;
}

// ─── Inner component — needs searchParams ─────────────────────────────────────

function AcceptInviteForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { error: toastError } = useToast();
  const set_auth = useAuthStore((s) => s.set_auth);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const token = searchParams.get("token") ?? "";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AcceptInviteFormValues>({
    resolver: zodResolver(acceptInviteSchema),
    defaultValues: { token },
  });

  const { mutate: acceptInvite, isPending } = useMutation({
    mutationFn: (payload: AcceptInviteFormValues) =>
      apiPost<AcceptInviteResponse>("/auth/invite/accept", payload),

    onSuccess: (data) => {
      setAccessToken(data.access_token);
      set_auth(data.me);
      router.replace("/dashboard");
    },

    onError: (err) => {
      const apiErr = err as { response?: { data?: { message?: string }; status?: number } };
      if (apiErr.response?.status === 400 || apiErr.response?.status === 404) {
        toastError(
          "Invitación inválida",
          "Este enlace de invitación ya fue usado o ha expirado.",
        );
      } else {
        toastError(
          "Error al aceptar invitación",
          apiErr.response?.data?.message ?? "Inténtalo de nuevo.",
        );
      }
    },
  });

  function onSubmit(values: AcceptInviteFormValues) {
    acceptInvite(values);
  }

  // Guard: no token
  if (!token) {
    return (
      <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="w-14 h-14 rounded-full bg-accent-50 dark:bg-accent-900/20 flex items-center justify-center">
            <Mail className="h-7 w-7 text-accent-600" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-foreground">Enlace de invitación inválido</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Este enlace no es válido. Pide al administrador de la clínica que te envíe una
              nueva invitación.
            </p>
          </div>
          <Link
            href="/login"
            className="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
          >
            Ir a iniciar sesión
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">Aceptar invitación</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Completa tu perfil para unirte a la clínica.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        {/* Hidden token */}
        <input type="hidden" {...register("token")} />

        {/* Full name */}
        <div className="space-y-1.5">
          <Label htmlFor="name" required>
            Nombre completo
          </Label>
          <Input
            id="name"
            type="text"
            autoComplete="name"
            placeholder="Dr. María López"
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
            aria-describedby={errors.password ? "password-error" : undefined}
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
          {errors.password && (
            <p id="password-error" className="text-xs text-destructive-600 dark:text-destructive-400">
              {errors.password.message}
            </p>
          )}
        </div>

        {/* Confirm password */}
        <div className="space-y-1.5">
          <Label htmlFor="confirm_password" required>
            Confirmar contraseña
          </Label>
          <Input
            id="confirm_password"
            type={showConfirm ? "text" : "password"}
            autoComplete="new-password"
            placeholder="Repite tu contraseña"
            aria-invalid={!!errors.confirm_password}
            aria-describedby={errors.confirm_password ? "confirm-error" : undefined}
            endAdornment={
              <button
                type="button"
                tabIndex={-1}
                onClick={() => setShowConfirm((v) => !v)}
                aria-label={showConfirm ? "Ocultar contraseña" : "Mostrar contraseña"}
                className="pointer-events-auto text-muted-foreground hover:text-foreground transition-colors"
              >
                {showConfirm ? (
                  <EyeOff className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Eye className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            }
            {...register("confirm_password")}
          />
          {errors.confirm_password && (
            <p id="confirm-error" className="text-xs text-destructive-600 dark:text-destructive-400">
              {errors.confirm_password.message}
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

        <Button type="submit" className="w-full" disabled={isPending}>
          {isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Creando tu cuenta...
            </>
          ) : (
            "Aceptar y crear cuenta"
          )}
        </Button>
      </form>

      <p className="mt-6 text-center">
        <Link
          href="/login"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Volver a iniciar sesión
        </Link>
      </p>
    </div>
  );
}

// ─── Page export — Suspense required for useSearchParams ─────────────────────

export default function AcceptInvitePage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8 animate-pulse">
          <div className="h-6 w-48 bg-slate-200 dark:bg-zinc-700 rounded mb-2" />
          <div className="h-4 w-full bg-slate-100 dark:bg-zinc-800 rounded mb-6" />
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-10 bg-slate-100 dark:bg-zinc-800 rounded" />
            ))}
            <div className="h-10 bg-primary-200 dark:bg-primary-900/40 rounded" />
          </div>
        </div>
      }
    >
      <AcceptInviteForm />
    </Suspense>
  );
}
