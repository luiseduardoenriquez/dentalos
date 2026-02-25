"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, MailCheck, ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/lib/hooks/use-toast";
import { apiPost } from "@/lib/api-client";
import { forgotPasswordSchema, type ForgotPasswordFormValues } from "@/lib/validations/auth";
import { useMutation } from "@tanstack/react-query";

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ForgotPasswordPage() {
  const { error: toastError } = useToast();
  const [submitted, setSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const { mutate: sendLink, isPending } = useMutation({
    mutationFn: (payload: ForgotPasswordFormValues) =>
      apiPost<void>("/auth/forgot-password", payload),

    onSuccess: () => {
      setSubmitted(true);
    },

    onError: (err) => {
      // For security we NEVER reveal whether the email exists.
      // Treat all errors the same as success to prevent email enumeration.
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status && status >= 500) {
        toastError(
          "Error del servidor",
          "No pudimos procesar tu solicitud. Inténtalo de nuevo en unos minutos.",
        );
        return;
      }
      // 404, 422, etc. — still show success message
      setSubmitted(true);
    },
  });

  function onSubmit(values: ForgotPasswordFormValues) {
    sendLink(values);
  }

  // ── Success state ──────────────────────────────────────────────────────────

  if (submitted) {
    return (
      <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="w-14 h-14 rounded-full bg-success-50 dark:bg-success-700/20 flex items-center justify-center">
            <MailCheck className="h-7 w-7 text-success-600" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-foreground">Revisa tu correo</h1>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              Si el correo está registrado en DentalOS, recibirás un enlace para
              restablecer tu contraseña en los próximos minutos.
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Revisa también tu carpeta de spam.
            </p>
          </div>
          <Link
            href="/login"
            className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Volver a iniciar sesión
          </Link>
        </div>
      </div>
    );
  }

  // ── Form state ─────────────────────────────────────────────────────────────

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">Recuperar contraseña</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ingresa tu correo y te enviaremos un enlace para recuperar el acceso.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
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

        <Button type="submit" className="w-full" disabled={isPending}>
          {isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Enviando enlace...
            </>
          ) : (
            "Enviar enlace de recuperación"
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
