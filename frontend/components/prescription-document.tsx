"use client";

import * as React from "react";
import { Download, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PrescriptionPreview } from "@/components/prescription-preview";
import { cn } from "@/lib/utils";
import type { PrescriptionResponse } from "@/lib/hooks/use-prescriptions";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PrescriptionDocumentProps {
  prescription: PrescriptionResponse;
  onDownloadPdf: () => void;
  onPrint: () => void;
  isDownloading?: boolean;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Full prescription document view with action bar.
 * Wraps PrescriptionPreview and adds PDF download + print buttons.
 */
export function PrescriptionDocument({
  prescription,
  onDownloadPdf,
  onPrint,
  isDownloading = false,
  className,
}: PrescriptionDocumentProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {/* ─── Action Bar ───────────────────────────────────────────────────── */}
      <div className="flex items-center justify-end gap-2 print:hidden">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onPrint}
          aria-label="Imprimir prescripción"
        >
          <Printer className="mr-1.5 h-4 w-4" />
          Imprimir
        </Button>
        <Button
          type="button"
          size="sm"
          onClick={onDownloadPdf}
          disabled={isDownloading}
          aria-label="Descargar PDF de la prescripción"
        >
          <Download className="mr-1.5 h-4 w-4" />
          {isDownloading ? "Descargando..." : "Descargar PDF"}
        </Button>
      </div>

      {/* ─── Prescription Preview ─────────────────────────────────────────── */}
      <div className="prescription-print-root">
        <PrescriptionPreview prescription={prescription} />
      </div>
    </div>
  );
}
