"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { CreditCard, ExternalLink, Loader2 } from "lucide-react";
import { apiPost } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatCurrency } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type FinancingProvider = "addi" | "sistecredito" | "mercadopago";

interface FinancingRequestPayload {
  provider: FinancingProvider;
  installments: number;
}

interface FinancingRequestResponse {
  application_id: string;
  status: string;
  redirect_url?: string;
  message: string;
}

// ─── Provider config ──────────────────────────────────────────────────────────

const PROVIDERS: { value: FinancingProvider; label: string }[] = [
  { value: "addi", label: "Addi" },
  { value: "sistecredito", label: "Sistecrédito" },
  { value: "mercadopago", label: "Mercado Pago" },
];

const INSTALLMENT_OPTIONS = [3, 6, 12, 24];

// ─── Component ────────────────────────────────────────────────────────────────

interface FinanceTreatmentButtonProps {
  invoiceId: string;
  amountCents: number;
  patientId: string;
  className?: string;
}

export function FinanceTreatmentButton({
  invoiceId,
  amountCents,
  className,
}: FinanceTreatmentButtonProps) {
  const [open, setOpen] = React.useState(false);
  const [provider, setProvider] = React.useState<FinancingProvider | "">("");
  const [installments, setInstallments] = React.useState<string>("12");
  const [result, setResult] = React.useState<FinancingRequestResponse | null>(null);

  const { mutate: requestFinancing, isPending, error } = useMutation({
    mutationFn: (payload: FinancingRequestPayload) =>
      apiPost<FinancingRequestResponse>(
        `/billing/invoices/${invoiceId}/financing-request`,
        payload,
      ),
    onSuccess: (data) => {
      setResult(data);
    },
  });

  function handleOpen() {
    setOpen(true);
    setProvider("");
    setInstallments("12");
    setResult(null);
  }

  function handleClose() {
    setOpen(false);
    setResult(null);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!provider) return;
    requestFinancing({
      provider,
      installments: Number(installments),
    });
  }

  const monthlyEstimateCents = amountCents / Number(installments);

  return (
    <>
      <Button variant="outline" size="sm" className={className} onClick={handleOpen}>
        <CreditCard className="mr-1.5 h-3.5 w-3.5" />
        Financiar
      </Button>

      <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Financiar este tratamiento</DialogTitle>
            <DialogDescription>
              Total a financiar:{" "}
              <strong className="text-foreground">{formatCurrency(amountCents, "COP")}</strong>
            </DialogDescription>
          </DialogHeader>

          {result ? (
            /* ─── Success state ─────────────────────────────────────────── */
            <div className="space-y-4 py-2">
              <div className="rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20 p-4 text-sm text-green-800 dark:text-green-300">
                {result.message}
              </div>
              {result.redirect_url && (
                <a
                  href={result.redirect_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:underline"
                >
                  Completar solicitud
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
              <DialogFooter>
                <Button onClick={handleClose}>Cerrar</Button>
              </DialogFooter>
            </div>
          ) : (
            /* ─── Request form ──────────────────────────────────────────── */
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Provider selection */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">
                  Seleccionar proveedor <span className="text-destructive">*</span>
                </label>
                <Select
                  value={provider}
                  onValueChange={(v) => setProvider(v as FinancingProvider)}
                  disabled={isPending}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Elige un proveedor de financiamiento" />
                  </SelectTrigger>
                  <SelectContent>
                    {PROVIDERS.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Installments */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">Cuotas</label>
                <div className="grid grid-cols-4 gap-2">
                  {INSTALLMENT_OPTIONS.map((n) => (
                    <button
                      key={n}
                      type="button"
                      disabled={isPending}
                      onClick={() => setInstallments(String(n))}
                      className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                        installments === String(n)
                          ? "border-primary-600 bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 dark:border-primary-500"
                          : "border-[hsl(var(--border))] bg-transparent text-foreground hover:border-primary-300 hover:bg-primary-50/50"
                      }`}
                    >
                      {n}x
                    </button>
                  ))}
                </div>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Aprox.{" "}
                  <strong className="text-foreground">
                    {formatCurrency(Math.ceil(monthlyEstimateCents), "COP")}
                  </strong>{" "}
                  / mes (sin interés estimado)
                </p>
              </div>

              {/* Error message */}
              {error && (
                <p className="text-xs text-destructive">
                  Error al procesar la solicitud. Intenta de nuevo.
                </p>
              )}

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleClose}
                  disabled={isPending}
                >
                  Cancelar
                </Button>
                <Button type="submit" disabled={isPending || !provider}>
                  {isPending ? (
                    <>
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                      Procesando...
                    </>
                  ) : (
                    "Solicitar financiamiento"
                  )}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
