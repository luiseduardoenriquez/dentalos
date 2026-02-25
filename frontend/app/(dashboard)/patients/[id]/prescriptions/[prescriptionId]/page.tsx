"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronLeft, ChevronRight, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { PrescriptionDocument } from "@/components/prescription-document";
import { usePrescription, usePrescriptionPdf } from "@/lib/hooks/use-prescriptions";

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function PrescriptionDetailSkeleton() {
  return (
    <div className="space-y-6 max-w-3xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>
      {/* Page title */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-48" />
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-32" />
        </div>
      </div>
      {/* Document skeleton */}
      <div className="rounded-xl border p-8 space-y-6">
        <Skeleton className="h-7 w-56 mx-auto" />
        <Skeleton className="h-4 w-32 mx-auto" />
        <div className="space-y-3 mt-6">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PrescriptionDetailPage() {
  const params = useParams<{ id: string; prescriptionId: string }>();

  const {
    data: prescription,
    isLoading,
    isError,
  } = usePrescription(params.id, params.prescriptionId);

  const { downloadPdf, isDownloading } = usePrescriptionPdf(
    params.id,
    params.prescriptionId,
  );

  function handlePrint() {
    window.print();
  }

  if (isLoading) {
    return <PrescriptionDetailSkeleton />;
  }

  if (isError || !prescription) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Prescripción no encontrada"
        description="La prescripción que buscas no existe o no tienes permiso para verla."
        action={{
          label: "Volver a prescripciones",
          href: `/patients/${params.id}/prescriptions`,
        }}
      />
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* ─── Breadcrumb ──────────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${params.id}`}
          className="hover:text-foreground transition-colors"
        >
          Detalle del paciente
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${params.id}/prescriptions`}
          className="hover:text-foreground transition-colors"
        >
          Prescripciones
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium truncate max-w-[120px]">
          Prescripción
        </span>
      </nav>

      {/* ─── Page Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Detalle de prescripción
        </h1>
        <Button variant="outline" size="sm" asChild className="w-fit print:hidden">
          <Link href={`/patients/${params.id}/prescriptions`}>
            <ChevronLeft className="mr-1.5 h-4 w-4" />
            Volver
          </Link>
        </Button>
      </div>

      {/* ─── Prescription Document ───────────────────────────────────────── */}
      <PrescriptionDocument
        prescription={prescription}
        onDownloadPdf={downloadPdf}
        onPrint={handlePrint}
        isDownloading={isDownloading}
      />
    </div>
  );
}
