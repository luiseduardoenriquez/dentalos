"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, Loader2, CheckCircle } from "lucide-react";
import { apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

interface SendPostopResponse {
  message: string;
  channel: string;
  sent_at: string;
}

interface SendPostopButtonProps {
  patientId: string;
  procedureType: string;
  /** Optional label override. */
  label?: string;
  variant?: "default" | "ghost";
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Small action button that sends post-operative instructions to a patient.
 *
 * POST /postop/send/{patientId}
 * Body: { procedure_type }
 *
 * Shows a transient "Enviado" state for 2s after success, then resets.
 */
export function SendPostopButton({
  patientId,
  procedureType,
  label = "Enviar post-op",
  variant = "default",
}: SendPostopButtonProps) {
  const { success, error: toastError } = useToast();
  const [sent, setSent] = React.useState(false);

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      apiPost<SendPostopResponse>(`/postop/send/${patientId}`, {
        procedure_type: procedureType,
      }),
    onSuccess: (data) => {
      const channelLabel =
        data.channel === "whatsapp"
          ? "WhatsApp"
          : data.channel === "email"
            ? "correo"
            : "portal";
      success(
        "Instrucciones enviadas",
        `Post-operatorio enviado al paciente por ${channelLabel}.`,
      );
      setSent(true);
      setTimeout(() => setSent(false), 2500);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo enviar las instrucciones. Intenta de nuevo.";
      toastError("Error al enviar", message);
    },
  });

  const isDisabled = isPending || sent;

  if (variant === "ghost") {
    return (
      <button
        onClick={() => mutate()}
        disabled={isDisabled}
        aria-label="Enviar instrucciones post-operatorias"
        className="inline-flex items-center gap-1.5 text-sm text-teal-600 hover:text-teal-700 hover:underline disabled:opacity-50 transition-colors"
      >
        {isPending ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : sent ? (
          <CheckCircle className="h-3.5 w-3.5 text-green-500" />
        ) : (
          <Send className="h-3.5 w-3.5" />
        )}
        {sent ? "Enviado" : label}
      </button>
    );
  }

  return (
    <button
      onClick={() => mutate()}
      disabled={isDisabled}
      aria-label="Enviar instrucciones post-operatorias"
      className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors disabled:opacity-60 bg-teal-50 text-teal-700 hover:bg-teal-100 dark:bg-teal-950/30 dark:text-teal-300 dark:hover:bg-teal-900/40"
    >
      {isPending ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : sent ? (
        <CheckCircle className="h-4 w-4 text-green-500" />
      ) : (
        <Send className="h-4 w-4" />
      )}
      {sent ? "Instrucciones enviadas" : label}
    </button>
  );
}
