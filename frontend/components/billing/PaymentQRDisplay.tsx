"use client";

import { useState } from "react";
import { Loader2, RefreshCw, QrCode } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiPost } from "@/lib/api-client";
import { formatCurrency, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type QRProvider = "nequi" | "daviplata";

interface QRCodeData {
  provider: QRProvider;
  qr_code_base64: string;
  amount_cents: number;
  expires_at: string;
  payment_reference: string | null;
}

interface PaymentQRDisplayProps {
  invoiceId: string;
  amountCents: number;
}

// ─── Provider Button ──────────────────────────────────────────────────────────

function ProviderButton({
  provider,
  selected,
  onSelect,
}: {
  provider: QRProvider;
  selected: boolean;
  onSelect: () => void;
}) {
  const isNequi = provider === "nequi";

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex-1 rounded-lg border-2 p-3 text-center transition-all",
        selected
          ? isNequi
            ? "border-purple-600 bg-purple-50 dark:bg-purple-900/20 shadow-sm"
            : "border-red-500 bg-red-50 dark:bg-red-900/20 shadow-sm"
          : "border-[hsl(var(--border))] hover:border-[hsl(var(--border))/80] hover:bg-[hsl(var(--muted)/0.5)]",
      )}
    >
      <span
        className={cn(
          "text-sm font-semibold",
          selected
            ? isNequi
              ? "text-purple-700 dark:text-purple-300"
              : "text-red-700 dark:text-red-300"
            : "text-[hsl(var(--muted-foreground))]",
        )}
      >
        {isNequi ? "Nequi" : "Daviplata"}
      </span>
      <p className="text-[10px] text-[hsl(var(--muted-foreground))] mt-0.5">
        {isNequi ? "Bancolombia" : "Davivienda"}
      </p>
    </button>
  );
}

// ─── QR Display ───────────────────────────────────────────────────────────────

function QRCodeDisplay({
  qrData,
  onReset,
}: {
  qrData: QRCodeData;
  onReset: () => void;
}) {
  const expiresAt = new Date(qrData.expires_at);
  const isExpired = expiresAt < new Date();

  return (
    <div className="flex flex-col items-center gap-4 text-center">
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        Escanea con{" "}
        <strong
          className={
            qrData.provider === "nequi" ? "text-purple-700" : "text-red-600"
          }
        >
          {qrData.provider === "nequi" ? "Nequi" : "Daviplata"}
        </strong>
      </p>

      {/* QR image */}
      <div
        className={cn(
          "inline-block rounded-xl border-2 p-3 bg-white",
          isExpired
            ? "border-red-300 opacity-50"
            : "border-[hsl(var(--border))]",
        )}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`data:image/png;base64,${qrData.qr_code_base64}`}
          alt="Código QR de pago"
          className="w-48 h-48 block"
        />
      </div>

      {/* Amount */}
      <p className="text-xl font-bold text-foreground tabular-nums">
        {formatCurrency(qrData.amount_cents, "COP")}
      </p>

      {/* Reference */}
      {qrData.payment_reference && (
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          Ref: <span className="font-mono">{qrData.payment_reference}</span>
        </p>
      )}

      {/* Expiry */}
      <p
        className={cn(
          "text-xs",
          isExpired
            ? "text-red-600 font-medium"
            : "text-[hsl(var(--muted-foreground))]",
        )}
      >
        {isExpired
          ? "Código expirado"
          : `Expira: ${new Intl.DateTimeFormat("es-CO", {
              timeStyle: "short",
            }).format(expiresAt)}`}
      </p>

      {/* Reset */}
      <button
        type="button"
        onClick={onReset}
        className="flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 hover:underline"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        Generar nuevo código
      </button>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function PaymentQRDisplay({ invoiceId, amountCents }: PaymentQRDisplayProps) {
  const [qrData, setQrData] = useState<QRCodeData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState<QRProvider>("nequi");

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiPost<QRCodeData>(
        `/billing/invoices/${invoiceId}/payment-qr`,
        { provider },
      );
      setQrData(data);
    } catch {
      setError("No se pudo generar el código QR. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <QrCode className="h-4 w-4 text-primary-600" />
          Pago con billetera móvil
        </CardTitle>
      </CardHeader>
      <CardContent>
        {qrData ? (
          <QRCodeDisplay qrData={qrData} onReset={() => setQrData(null)} />
        ) : (
          <div className="space-y-4">
            {/* Amount summary */}
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Monto a cobrar:{" "}
              <span className="font-semibold text-foreground tabular-nums">
                {formatCurrency(amountCents, "COP")}
              </span>
            </p>

            {/* Provider selector */}
            <div className="flex gap-3">
              <ProviderButton
                provider="nequi"
                selected={provider === "nequi"}
                onSelect={() => setProvider("nequi")}
              />
              <ProviderButton
                provider="daviplata"
                selected={provider === "daviplata"}
                onSelect={() => setProvider("daviplata")}
              />
            </div>

            {/* Error */}
            {error && (
              <p className="text-xs text-destructive">{error}</p>
            )}

            {/* Generate button */}
            <Button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generando...
                </>
              ) : (
                <>
                  <QrCode className="mr-2 h-4 w-4" />
                  Generar código QR
                </>
              )}
            </Button>

            <p className="text-[11px] text-center text-[hsl(var(--muted-foreground))]">
              El código expira a los 10 minutos de ser generado
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
