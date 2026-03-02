"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { portalApiPost } from "@/lib/portal-api-client";
import { PaymentQRDisplay } from "@/components/portal/NequiPayButton";

// ─── Types ────────────────────────────────────────────────────────────────────

interface QRResponse {
  qr_image_url: string;
  qr_code: string;
  deep_link: string;
  expires_at: string;
  reference: string;
}

interface DaviplataPayButtonProps {
  invoiceId: string;
  amountCents: number;
}

// ─── DaviplataPayButton ───────────────────────────────────────────────────────

/**
 * Generates a Daviplata QR for portal invoice payment.
 *
 * On click: POST /portal/invoices/{invoiceId}/pay/daviplata
 * On success: renders PaymentQRDisplay inline.
 * Brand colors: Davivienda red (#E11D48).
 */
export function DaviplataPayButton({
  invoiceId,
  amountCents,
}: DaviplataPayButtonProps) {
  const [qr, setQr] = React.useState<QRResponse | null>(null);

  const { mutate: generateQR, isPending, error } = useMutation({
    mutationFn: () =>
      portalApiPost<QRResponse>(
        `/portal/invoices/${invoiceId}/pay/daviplata`,
        { amount_cents: amountCents },
      ),
    onSuccess: (data) => setQr(data),
  });

  if (qr) {
    return (
      <div className="space-y-3">
        <PaymentQRDisplay qr={qr} amountCents={amountCents} brand="daviplata" />
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
        className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#E11D48] text-white px-5 py-3 text-sm font-semibold hover:bg-[#BE123C] disabled:opacity-60 transition-colors"
      >
        {isPending ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Generando QR...
          </>
        ) : (
          <>
            <DaviplataIcon />
            Pagar con Daviplata
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

function DaviplataIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" opacity="0.2" />
      <text x="50%" y="55%" dominantBaseline="middle" textAnchor="middle" fontSize="10" fontWeight="bold">D</text>
    </svg>
  );
}
