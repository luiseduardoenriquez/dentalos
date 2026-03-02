"use client";

import * as React from "react";
import { Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import type { CashMovement } from "@/components/billing/CashMovementList";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DailyReportProps {
  registerName: string;
  openedAt: string;
  closedAt: string | null;
  openingBalanceCents: number;
  closingBalanceCents: number | null;
  totalIncomeCents: number;
  totalExpenseCents: number;
  netBalanceCents: number;
  movements: CashMovement[];
  clinicName?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MOVEMENT_TYPE_LABELS: Record<string, string> = {
  income: "Ingreso",
  expense: "Egreso",
  adjustment: "Ajuste",
};

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: "Efectivo",
  card: "Tarjeta",
  transfer: "Transferencia",
  nequi: "Nequi",
  daviplata: "Daviplata",
  insurance: "Aseguradora",
  other: "Otro",
};

// ─── Component ────────────────────────────────────────────────────────────────

export function DailyReport({
  registerName,
  openedAt,
  closedAt,
  openingBalanceCents,
  closingBalanceCents,
  totalIncomeCents,
  totalExpenseCents,
  netBalanceCents,
  movements,
  clinicName,
}: DailyReportProps) {
  const handlePrint = () => {
    window.print();
  };

  const expectedClosing = openingBalanceCents + totalIncomeCents - totalExpenseCents;
  const difference =
    closingBalanceCents !== null ? closingBalanceCents - expectedClosing : null;

  return (
    <>
      {/* Print button — hidden when printing */}
      <div className="print:hidden flex justify-end mb-4">
        <Button variant="outline" size="sm" onClick={handlePrint}>
          <Printer className="mr-1.5 h-4 w-4" />
          Imprimir reporte
        </Button>
      </div>

      {/*
       * Report body — styled for both screen and print.
       * @media print styles are applied via Tailwind print: variants.
       */}
      <div
        id="daily-report"
        className="bg-white dark:bg-white text-slate-900 rounded-lg border p-6 max-w-2xl mx-auto
                   print:border-0 print:rounded-none print:p-0 print:max-w-full print:shadow-none"
      >
        {/* Header */}
        <div className="text-center mb-6">
          {clinicName && (
            <p className="text-sm text-slate-500 mb-1">{clinicName}</p>
          )}
          <h1 className="text-xl font-bold text-slate-900">
            Reporte Diario de Caja
          </h1>
          <p className="text-base font-medium text-slate-700 mt-1">{registerName}</p>
          <p className="text-sm text-slate-500 mt-1">
            Apertura: {formatDateTime(openedAt)}
            {closedAt && (
              <span> &nbsp;|&nbsp; Cierre: {formatDateTime(closedAt)}</span>
            )}
          </p>
        </div>

        <Separator className="my-4 print:border-slate-300" />

        {/* Summary grid */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="space-y-3">
            <ReportRow
              label="Saldo inicial"
              value={formatCurrency(openingBalanceCents, "COP")}
            />
            <ReportRow
              label="Total ingresos"
              value={formatCurrency(totalIncomeCents, "COP")}
              valueClass="text-green-700 font-semibold"
            />
            <ReportRow
              label="Total egresos"
              value={formatCurrency(totalExpenseCents, "COP")}
              valueClass="text-red-700 font-semibold"
            />
          </div>
          <div className="space-y-3">
            <ReportRow
              label="Saldo esperado"
              value={formatCurrency(expectedClosing, "COP")}
            />
            {closingBalanceCents !== null && (
              <ReportRow
                label="Saldo de cierre"
                value={formatCurrency(closingBalanceCents, "COP")}
                valueClass="font-semibold"
              />
            )}
            {difference !== null && (
              <ReportRow
                label="Diferencia"
                value={
                  (difference >= 0 ? "+" : "") +
                  formatCurrency(difference, "COP")
                }
                valueClass={
                  difference === 0
                    ? "text-green-700 font-semibold"
                    : difference > 0
                    ? "text-blue-700 font-semibold"
                    : "text-red-700 font-semibold"
                }
              />
            )}
          </div>
        </div>

        {/* Net balance highlight */}
        <div className="rounded-lg bg-slate-50 border border-slate-200 px-5 py-3 flex items-center justify-between mb-6">
          <span className="text-base font-bold text-slate-900">Saldo neto del día</span>
          <span
            className={
              netBalanceCents >= 0
                ? "text-xl font-bold text-green-700"
                : "text-xl font-bold text-red-700"
            }
          >
            {formatCurrency(netBalanceCents, "COP")}
          </span>
        </div>

        <Separator className="my-4 print:border-slate-300" />

        {/* Movements detail */}
        <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">
          Detalle de movimientos
        </h2>

        {movements.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-4">
            No hubo movimientos en esta sesión.
          </p>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left pb-2 font-semibold text-slate-600">Hora</th>
                <th className="text-left pb-2 font-semibold text-slate-600">Tipo</th>
                <th className="text-left pb-2 font-semibold text-slate-600">Descripción</th>
                <th className="text-left pb-2 font-semibold text-slate-600">Método</th>
                <th className="text-right pb-2 font-semibold text-slate-600">Monto</th>
              </tr>
            </thead>
            <tbody>
              {movements.map((m) => (
                <tr key={m.id} className="border-b border-slate-100">
                  <td className="py-1.5 text-slate-500 tabular-nums whitespace-nowrap">
                    {new Intl.DateTimeFormat("es-CO", {
                      timeStyle: "short",
                    }).format(new Date(m.created_at))}
                  </td>
                  <td className="py-1.5">
                    {MOVEMENT_TYPE_LABELS[m.type] ?? m.type}
                  </td>
                  <td className="py-1.5 text-slate-600 max-w-[200px] truncate">
                    {m.description ?? "—"}
                  </td>
                  <td className="py-1.5 text-slate-500">
                    {m.payment_method
                      ? (PAYMENT_METHOD_LABELS[m.payment_method] ?? m.payment_method)
                      : "—"}
                  </td>
                  <td
                    className={
                      "py-1.5 text-right tabular-nums font-medium " +
                      (m.type === "income"
                        ? "text-green-700"
                        : m.type === "expense"
                        ? "text-red-700"
                        : "text-yellow-700")
                    }
                  >
                    {m.type === "income" ? "+" : m.type === "expense" ? "−" : "±"}
                    {formatCurrency(m.amount_cents, "COP")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Footer */}
        <div className="mt-8 pt-4 border-t border-slate-200 text-center text-xs text-slate-400">
          Generado el {formatDateTime(new Date().toISOString())} &nbsp;·&nbsp; DentalOS
        </div>
      </div>
    </>
  );
}

// ─── Helper ───────────────────────────────────────────────────────────────────

function ReportRow({
  label,
  value,
  valueClass = "text-slate-900",
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-slate-500">{label}</span>
      <span className={`text-sm tabular-nums ${valueClass}`}>{value}</span>
    </div>
  );
}
