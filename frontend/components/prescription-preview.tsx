"use client";

import * as React from "react";
import { formatDate } from "@/lib/utils";
import { VIA_LABELS } from "@/lib/validations/prescription";
import type { PrescriptionResponse } from "@/lib/hooks/use-prescriptions";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PrescriptionPreviewProps {
  prescription: PrescriptionResponse;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Read-only prescription display suitable for screen viewing and printing.
 * Renders a document-like card layout with the medication table.
 */
export function PrescriptionPreview({ prescription, className }: PrescriptionPreviewProps) {
  return (
    <div
      className={cn(
        "bg-white dark:bg-white rounded-xl border border-[hsl(var(--border))] p-8 shadow-sm print:shadow-none print:border print:rounded-none",
        "text-foreground",
        className,
      )}
    >
      {/* ─── Document Header ──────────────────────────────────────────────── */}
      <div className="border-b border-[hsl(var(--border))] pb-6 mb-6">
        <h2 className="text-xl font-bold tracking-widest uppercase text-center text-foreground">
          Prescripción Médica
        </h2>
        <p className="text-sm text-center text-[hsl(var(--muted-foreground))] mt-1">
          Fecha:{" "}
          <span className="font-medium text-foreground">
            {formatDate(prescription.created_at)}
          </span>
        </p>
      </div>

      {/* ─── Medications Table ────────────────────────────────────────────── */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-[hsl(var(--border))]">
              <th className="text-left py-2 pr-3 font-semibold text-[hsl(var(--muted-foreground))] w-6">
                #
              </th>
              <th className="text-left py-2 pr-3 font-semibold text-[hsl(var(--muted-foreground))]">
                Medicamento
              </th>
              <th className="text-left py-2 pr-3 font-semibold text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Dosis
              </th>
              <th className="text-left py-2 pr-3 font-semibold text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Frecuencia
              </th>
              <th className="text-left py-2 pr-3 font-semibold text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Duración
              </th>
              <th className="text-left py-2 pr-3 font-semibold text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                Vía
              </th>
              <th className="text-left py-2 font-semibold text-[hsl(var(--muted-foreground))]">
                Instrucciones
              </th>
            </tr>
          </thead>
          <tbody>
            {prescription.medications.map((med, idx) => (
              <tr
                key={idx}
                className="border-b border-[hsl(var(--border))] last:border-0 align-top"
              >
                <td className="py-3 pr-3 text-[hsl(var(--muted-foreground))] font-medium">
                  {idx + 1}
                </td>
                <td className="py-3 pr-3 font-medium text-foreground">{med.name}</td>
                <td className="py-3 pr-3 text-foreground whitespace-nowrap">{med.dosis}</td>
                <td className="py-3 pr-3 text-foreground whitespace-nowrap">{med.frecuencia}</td>
                <td className="py-3 pr-3 text-foreground whitespace-nowrap">
                  {med.duracion_dias}{" "}
                  {med.duracion_dias === 1 ? "día" : "días"}
                </td>
                <td className="py-3 pr-3 text-foreground whitespace-nowrap">
                  {VIA_LABELS[med.via] ?? med.via}
                </td>
                <td className="py-3 text-[hsl(var(--muted-foreground))]">
                  {med.instrucciones ?? (
                    <span className="text-[hsl(var(--muted-foreground))]">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ─── Notes Section ────────────────────────────────────────────────── */}
      {prescription.notes && (
        <div className="mt-6 pt-6 border-t border-[hsl(var(--border))]">
          <p className="text-xs font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-2">
            Notas
          </p>
          <p className="text-sm text-foreground whitespace-pre-wrap">{prescription.notes}</p>
        </div>
      )}

      {/* ─── Print-only Footer ────────────────────────────────────────────── */}
      <div className="hidden print:block mt-12 pt-6 border-t border-gray-300">
        <div className="flex justify-between items-end">
          <div>
            <div className="h-px w-48 bg-gray-400 mb-1" />
            <p className="text-xs text-gray-500">Firma del médico</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-400">DentalOS</p>
            <p className="text-xs text-gray-400">{formatDate(prescription.created_at)}</p>
          </div>
        </div>
      </div>

      {/* ─── Print Styles (injected inline) ──────────────────────────────── */}
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .prescription-print-root,
          .prescription-print-root * {
            visibility: visible;
          }
          .prescription-print-root {
            position: absolute;
            inset: 0;
            margin: 0;
            padding: 2rem;
          }
        }
      `}</style>
    </div>
  );
}
