"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, CreditCard, AlertCircle } from "lucide-react";
import Link from "next/link";
import { portalApiGet } from "@/lib/portal-api-client";
import { NequiPayButton } from "@/components/portal/NequiPayButton";
import { DaviplataPayButton } from "@/components/portal/DaviplataPayButton";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PortalInvoiceDetail {
  id: string;
  invoice_number: string | null;
  date: string;
  total: number;
  paid: number;
  balance: number;
  status: "pending" | "partial" | "paid" | "cancelled";
  line_items: {
    description: string;
    quantity: number;
    unit_price: number;
    total: number;
  }[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatCurrency(cents: number) {
  return (cents / 100).toLocaleString("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 0,
  });
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="space-y-6 max-w-md mx-auto animate-pulse">
      <div className="h-6 w-36 rounded bg-slate-200 dark:bg-zinc-700" />
      <div className="h-28 rounded-xl bg-slate-100 dark:bg-zinc-800" />
      <div className="h-16 rounded-xl bg-slate-100 dark:bg-zinc-800" />
      <div className="h-16 rounded-xl bg-slate-100 dark:bg-zinc-800" />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * /portal/invoices/[id]/pay
 *
 * Portal invoice payment page.
 * Shows the outstanding balance and Nequi + Daviplata payment options.
 */
export default function PortalInvoicePayPage() {
  const params = useParams<{ id: string }>();
  const invoiceId = params.id;

  const { data: invoice, isLoading, isError } = useQuery({
    queryKey: ["portal", "invoices", invoiceId],
    queryFn: () =>
      portalApiGet<PortalInvoiceDetail>(`/portal/invoices/${invoiceId}`),
    enabled: Boolean(invoiceId),
    staleTime: 30_000,
  });

  // ─── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) return <PageSkeleton />;

  // ─── Error ──────────────────────────────────────────────────────────────────
  if (isError || !invoice) {
    return (
      <div className="max-w-md mx-auto flex flex-col items-center justify-center py-16 gap-3 text-center">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-sm font-medium text-red-600 dark:text-red-400">
          No se pudo cargar la factura
        </p>
        <Link
          href="/portal/invoices"
          className="text-sm text-teal-600 hover:underline"
        >
          Volver a mis facturas
        </Link>
      </div>
    );
  }

  // ─── Already paid ────────────────────────────────────────────────────────────
  if (invoice.status === "paid") {
    return (
      <div className="max-w-md mx-auto space-y-4">
        <Link
          href="/portal/invoices"
          className="inline-flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Volver a mis facturas
        </Link>
        <div className="rounded-xl border border-green-200 bg-green-50 dark:bg-green-950/20 dark:border-green-800 px-6 py-8 text-center">
          <p className="text-lg font-bold text-green-700 dark:text-green-300">
            Factura pagada
          </p>
          <p className="mt-2 text-sm text-green-600 dark:text-green-400">
            Esta factura ya fue pagada en su totalidad.
          </p>
        </div>
      </div>
    );
  }

  // ─── Cancelled ───────────────────────────────────────────────────────────────
  if (invoice.status === "cancelled") {
    return (
      <div className="max-w-md mx-auto space-y-4">
        <Link
          href="/portal/invoices"
          className="inline-flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Volver a mis facturas
        </Link>
        <div className="rounded-xl border border-slate-200 bg-slate-50 dark:bg-zinc-900 px-6 py-8 text-center">
          <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
            Esta factura fue anulada y no se puede pagar.
          </p>
        </div>
      </div>
    );
  }

  const amountToPay = invoice.balance;

  // ─── Payment page ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 max-w-md mx-auto">
      {/* Back */}
      <Link
        href="/portal/invoices"
        className="inline-flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors"
      >
        <ChevronLeft className="h-4 w-4" />
        Volver a mis facturas
      </Link>

      {/* Page title */}
      <div>
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))] flex items-center gap-2">
          <CreditCard className="h-5 w-5 text-teal-600" />
          Pagar factura
        </h1>
        {invoice.invoice_number && (
          <p className="mt-0.5 text-sm text-[hsl(var(--muted-foreground))]">
            Factura {invoice.invoice_number} &mdash;{" "}
            {new Date(invoice.date).toLocaleDateString("es-CO", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </p>
        )}
      </div>

      {/* Amount summary */}
      <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-5 py-5 space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-[hsl(var(--muted-foreground))]">
            Total factura
          </span>
          <span className="font-medium">{formatCurrency(invoice.total)}</span>
        </div>
        {invoice.paid > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-[hsl(var(--muted-foreground))]">
              Ya pagado
            </span>
            <span className="font-medium text-green-600 dark:text-green-400">
              {formatCurrency(invoice.paid)}
            </span>
          </div>
        )}
        <div className="border-t border-[hsl(var(--border))] pt-3 flex justify-between">
          <span className="text-sm font-semibold text-[hsl(var(--foreground))]">
            Por pagar
          </span>
          <span className="text-xl font-bold text-[hsl(var(--foreground))]">
            {formatCurrency(amountToPay)}
          </span>
        </div>
      </div>

      {/* Payment methods */}
      <div>
        <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-3">
          Selecciona un método de pago
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <NequiPayButton invoiceId={invoiceId} amountCents={amountToPay} />
          <DaviplataPayButton
            invoiceId={invoiceId}
            amountCents={amountToPay}
          />
        </div>
      </div>

      {/* Security note */}
      <p className="text-xs text-center text-[hsl(var(--muted-foreground))]">
        El pago es procesado de forma segura. El QR expira en 10 minutos.
      </p>
    </div>
  );
}
