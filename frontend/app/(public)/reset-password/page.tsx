"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Eye, EyeOff, Loader2, ArrowLeft, ShieldCheck } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/lib/hooks/use-toast";
import { apiPost } from "@/lib/api-client";
import { resetPasswordSchema, type ResetPasswordFormValues } from "@/lib/validations/auth";

// ─── Inner component — needs searchParams ─────────────────────────────────────

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { success: toastSuccess, error: toastError } = useToast();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const token = searchParams.get("token") ?? "";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { token },
  });

  const { mutate: resetPassword, isPending } = useMutation({
    mutationFn: (payload: ResetPasswordFormValues) =>
      apiPost<void>("/auth/reset-password", payload),

    onSuccess: () => {
      toastSuccess(
        "Contraseña restablecida",
        "Tu contraseña fue actualizada. Inicia sesión con tu nueva contraseña.",
      );
      router.replace("/login");
    },

    onError: (err) => {
      const apiErr = err as { response?: { data?: { message?: string }; status?: number } };
      if (apiErr.response?.status === 400) {
        toastError(
          "Enlace inválido o expirado",
          "El enlace de recuperación ha vencido. Solicita uno nuevo.",
        );
      } else {
        toastError(
          "Error al restablecer",
          apiErr.response?.data?.message ?? "Inténtalo de nuevo.",
        );
      }
    },
  });

  function onSubmit(values: ResetPasswordFormValues) {
    resetPassword(values);
  }

  // Guard: no token in URL
  if (!token) {
    return (
      <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="w-14 h-14 rounded-full bg-destructive-50 dark:bg-destructive-900/20 flex items-center justify-center">
            <ShieldCheck className="h-7 w-7 text-destructive-600" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-foreground">Enlace inválido</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Este enlace de recuperación no es válido o ya fue utilizado.
            </p>
          </div>
          <Link
            href="/forgot-password"
            className="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
          >
            Solicitar un nuevo enlace
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">Restablecer contraseña</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Crea una nueva contraseña segura para tu cuenta.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        {/* Hidden token field */}
        <input type="hidden" {...register("token")} />

        {/* New password */}
        <div className="space-y-1.5">
          <Label htmlFor="new_password" required>
            Nueva contraseña
          </Label>
          <Input
            id="new_password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            placeholder="Mínimo 8 caracteres"
            aria-invalid={!!errors.new_password}
            aria-describedby={errors.new_password ? "new-password-error" : undefined}
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
            {...register("new_password")}
          />
          {errors.new_password && (
            <p id="new-password-error" className="text-xs text-destructive-600 dark:text-destructive-400">
              {errors.new_password.message}
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
            placeholder="Repite tu nueva contraseña"
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

        <Button type="submit" className="w-full" disabled={isPending}>
          {isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Restableciendo...
            </>
          ) : (
            "Restablecer contraseña"
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

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8 animate-pulse">
          <div className="h-6 w-48 bg-slate-200 dark:bg-zinc-700 rounded mb-2" />
          <div className="h-4 w-full bg-slate-100 dark:bg-zinc-800 rounded mb-6" />
          <div className="space-y-4">
            <div className="h-10 bg-slate-100 dark:bg-zinc-800 rounded" />
            <div className="h-10 bg-slate-100 dark:bg-zinc-800 rounded" />
            <div className="h-10 bg-primary-200 dark:bg-primary-900/40 rounded" />
          </div>
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
