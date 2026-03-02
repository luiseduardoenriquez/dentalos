"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Smartphone } from "lucide-react";
import { portalApiPost } from "@/lib/portal-api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

interface QRResponse {
  qr_image_url: string;
  qr_code: string;
  deep_link: string;
  expires_at: string;
  reference: string;
}

interface PaymentQRDisplayProps {
  qr: QRResponse;
  amountCents: number;
  brand: "nequi" | "daviplata";
}

interface NequiPayButtonProps {
  invoiceId: string;
  amountCents: number;
}

// ─── PaymentQRDisplay ─────────────────────────────────────────────────────────

/**
 * Shared QR display panel used by both Nequi and Daviplata buttons.
 */
export function PaymentQRDisplay({
  qr,
  amountCents,
  brand,
}: PaymentQRDisplayProps) {
  const formattedAmount = (amountCents / 100).toLocaleString("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
  });

  const expiresLabel = new Date(qr.expires_at).toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
  });

  const brandColors =
    brand === "nequi"
      ? "border-purple-200 bg-purple-50 dark:bg-purple-950/20 dark:border-purple-800"
      : "border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-800";

  const brandText =
    brand === "nequi" ? "Pagar con Nequi" : "Pagar con Daviplata";

  return (
    <div
      className={`rounded-xl border p-5 space-y-4 text-center ${brandColors}`}
    >
      <p className="text-sm font-semibold text-[hsl(var(--foreground))]">
        {brandText}
      </p>

      <p className="text-2xl font-bold text-[hsl(var(--foreground))]">
        {formattedAmount}
      </p>

      {/* QR image */}
      <div className="flex justify-center">
        {qr.qr_image_url ? (
          <img
            src={qr.qr_image_url}
            alt={`Código QR ${brand}`}
            width={180}
            height={180}
            className="rounded-lg border border-[hsl(var(--border))]"
          />
        ) : (
          <div className="w-[180px] h-[180px] rounded-lg border border-[hsl(var(--border))] flex items-center justify-center bg-white">
            <span className="text-xs text-[hsl(var(--muted-foreground))]">
              QR no disponible
            </span>
          </div>
        )}
      </div>

      {/* Reference */}
      <p className="text-xs text-[hsl(var(--muted-foreground))]">
        Ref:{" "}
        <span className="font-mono font-medium text-[hsl(var(--foreground))]">
          {qr.reference}
        </span>
      </p>

      {/* Deep link (mobile) */}
      {qr.deep_link && (
        <a
          href={qr.deep_link}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-opacity hover:opacity-90 ${
            brand === "nequi"
              ? "bg-[#7C3AED]"
              : "bg-[#E11D48]"
          }`}
        >
          <Smartphone className="h-4 w-4" />
          Abrir en la app
        </a>
      )}

      <p className="text-xs text-[hsl(var(--muted-foreground))]">
        Expira a las {expiresLabel}. Escanea el QR desde tu app{" "}
        {brand === "nequi" ? "Nequi" : "Daviplata"}.
      </p>
    </div>
  );
}

// ─── NequiPayButton ───────────────────────────────────────────────────────────

/**
 * Generates a Nequi QR for portal invoice payment.
 *
 * On click: POST /portal/invoices/{invoiceId}/pay/nequi
 * On success: renders PaymentQRDisplay inline.
 */
export function NequiPayButton({
  invoiceId,
  amountCents,
}: NequiPayButtonProps) {
  const [qr, setQr] = React.useState<QRResponse | null>(null);

  const { mutate: generateQR, isPending, error } = useMutation({
    mutationFn: () =>
      portalApiPost<QRResponse>(
        `/portal/invoices/${invoiceId}/pay/nequi`,
        { amount_cents: amountCents },
      ),
    onSuccess: (data) => setQr(data),
  });

  if (qr) {
    return (
      <div className="space-y-3">
        <PaymentQRDisplay qr={qr} amountCents={amountCents} brand="nequi" />
        <button
          onClick={() => setQr(null)}
          className="w-full text-xs text-[hsl(var(--muted-foreground))] hover:underline"
        >
          Cancelar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <button
        onClick={() => generateQR()}
        disabled={isPending}
        className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#7C3AED] text-white px-5 py-3 text-sm font-semibold hover:bg-[#6D28D9] disabled:opacity-60 transition-colors"
      >
        {isPending ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Generando QR...
          </>
        ) : (
          <>
            <NequiIcon />
            Pagar con Nequi
          </>
        )}
      </button>
      {error && (
        <p className="text-xs text-red-500 text-center">
          No se pudo generar el QR. Intenta de nuevo.
        </p>
      )}
    </div>
  );
}

// ─── Brand icon ───────────────────────────────────────────────────────────────

function NequiIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" opacity="0.2" />
      <text x="50%" y="55%" dominantBaseline="middle" textAnchor="middle" fontSize="10" fontWeight="bold">N</text>
    </svg>
  );
}
