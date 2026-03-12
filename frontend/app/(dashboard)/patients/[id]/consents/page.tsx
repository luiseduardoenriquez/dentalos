"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Plus, ChevronRight, FileText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ConsentStatusBadge } from "@/components/consent-status-badge";
import { useConsents } from "@/lib/hooks/use-consents";
import { usePatient } from "@/lib/hooks/use-patients";
import { formatDate } from "@/lib/utils";

// ─── Category Labels ──────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  general: "General",
  surgery: "Cirugía",
  sedation: "Sedación",
  orthodontics: "Ortodoncia",
  implants: "Implantes",
  endodontics: "Endodoncia",
  pediatric: "Pediátrico",
};

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function ConsentListSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-9 w-44 rounded-md" />
      </div>
      <Card>
        <CardContent className="p-0">
          <div className="divide-y divide-[hsl(var(--border))]">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-4 p-4">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-5 w-20 rounded-full" />
                <Skeleton className="h-4 w-24 ml-auto" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ConsentsListPage() {
  const params = useParams<{ id: string }>();
  const patient_id = params.id;

  const [page] = React.useState(1);
  const page_size = 20;

  const { data: patient, isLoading: is_loading_patient } = usePatient(patient_id);
  const {
    data: consents_data,
    isLoading: is_loading_consents,
    isError,
  } = useConsents(patient_id, page, page_size);

  const is_loading = is_loading_patient || is_loading_consents;

  if (is_loading) {
    return <ConsentListSkeleton />;
  }

  if (isError) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Error al cargar consentimientos"
        description="No se pudieron cargar los consentimientos. Intenta de nuevo."
        action={{ label: "Reintentar", onClick: () => window.location.reload() }}
      />
    );
  }

  const consents = consents_data?.items ?? [];

  return (
    <div className="space-y-6">
      {/* ─── Breadcrumb ────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/patients" className="hover:text-foreground transition-colors">
          Pacientes
        </Link>
        <ChevronRight className="h-4 w-4" />
        <Link
          href={`/patients/${patient_id}`}
          className="hover:text-foreground transition-colors truncate max-w-[150px]"
        >
          {patient?.full_name ?? "Paciente"}
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium">Consentimientos</span>
      </nav>

      {/* ─── Header ────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Consentimientos informados</h1>
          <p className="mt-0.5 text-sm text-[hsl(var(--muted-foreground))]">
            {consents_data?.total ?? 0}{" "}
            consentimiento{(consents_data?.total ?? 0) !== 1 ? "s" : ""} registrado
            {(consents_data?.total ?? 0) !== 1 ? "s" : ""}
          </p>
        </div>
        <Button asChild>
          <Link href={`/patients/${patient_id}/consents/new`}>
            <Plus className="mr-1.5 h-4 w-4" />
            Nuevo Consentimiento
          </Link>
        </Button>
      </div>

      {/* ─── Table or Empty State ──────────────────────────────────── */}
      {consents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="Sin consentimientos"
          description="Este paciente no tiene consentimientos registrados. Crea el primero para comenzar."
          action={{
            label: "Nuevo Consentimiento",
            href: `/patients/${patient_id}/consents/new`,
          }}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Título</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Fecha</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {consents.map((consent) => (
                  <TableRow
                    key={consent.id}
                    className="cursor-pointer hover:bg-[hsl(var(--muted))/50] transition-colors"
                  >
                    <TableCell>
                      <Link
                        href={`/patients/${patient_id}/consents/${consent.id}`}
                        className="font-medium text-foreground hover:text-primary-600 transition-colors"
                      >
                        {consent.title}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <ConsentStatusBadge status={consent.status} />
                    </TableCell>
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                      {formatDate(consent.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
