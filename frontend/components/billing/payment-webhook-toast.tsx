"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/lib/hooks/use-toast";
import { formatCurrency } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PaymentWebhookEvent {
  type: "payment.confirmed" | "payment.failed";
  invoice_id: string;
  patient_name: string;
  amount_cents: number;
  currency: string;
  method: string;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * usePaymentWebhookToast — Listens for payment webhook SSE events and shows
 * toast notifications on successful or failed payments.
 *
 * Meant to be mounted once in the dashboard layout.
 */
export function usePaymentWebhookToast() {
  const { success, error: toastError } = useToast();
  const queryClient = useQueryClient();

  React.useEffect(() => {
    function handlePaymentEvent(event: CustomEvent<PaymentWebhookEvent>) {
      const detail = event.detail;

      if (detail.type === "payment.confirmed") {
        success(
          "Pago recibido",
          `${detail.patient_name} — ${formatCurrency(detail.amount_cents)} ${detail.currency} (${detail.method})`,
        );
        // Invalidate relevant queries so UI updates
        queryClient.invalidateQueries({ queryKey: ["invoices"] });
        queryClient.invalidateQueries({ queryKey: ["billing_summary"] });
        queryClient.invalidateQueries({ queryKey: ["payments"] });
      } else if (detail.type === "payment.failed") {
        toastError(
          "Pago fallido",
          `${detail.patient_name} — el pago de ${formatCurrency(detail.amount_cents)} ${detail.currency} no se procesó.`,
        );
      }
    }

    window.addEventListener(
      "dentalos:payment-webhook",
      handlePaymentEvent as EventListener,
    );
    return () => {
      window.removeEventListener(
        "dentalos:payment-webhook",
        handlePaymentEvent as EventListener,
      );
    };
  }, [success, toastError, queryClient]);
}

// ─── Utility — dispatch from SSE/WebSocket handler ────────────────────────────

/**
 * Call this from your SSE or WebSocket payment listener to trigger the toast.
 */
export function dispatchPaymentWebhookEvent(data: PaymentWebhookEvent) {
  window.dispatchEvent(
    new CustomEvent("dentalos:payment-webhook", { detail: data }),
  );
}
