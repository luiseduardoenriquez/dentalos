"use client";

import * as React from "react";
import Link from "next/link";
import { FilePlus, FileText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import {
  useConsentTemplates,
  type ConsentTemplateResponse,
} from "@/lib/hooks/use-consent-templates";

// ─── Category Labels ─────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  general: "General",
  surgery: "Cirugía",
  sedation: "Sedación",
  orthodontics: "Ortodoncia",
  implants: "Implantes",
  endodontics: "Endodoncia",
  pediatric: "Pediátrico",
};

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function ConsentTemplatesListSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-9 w-36" />
      </div>
      <div className="rounded-xl border">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-0">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-12" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Column Definitions ──────────────────────────────────────────────────────

function buildColumns(): ColumnDef<ConsentTemplateResponse>[] {
  return [
    {
      key: "name",
      header: "Nombre",
      sortable: false,
      cell: (row) => (
        <span className="text-sm font-medium text-foreground">{row.name}</span>
      ),
    },
    {
      key: "category",
      header: "Categoría",
      cell: (row) => (
        <Badge variant="outline" className="text-xs">
          {CATEGORY_LABELS[row.category] ?? row.category}
        </Badge>
      ),
    },
    {
      key: "version",
      header: "Versión",
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))] font-mono">
          v{row.version}
        </span>
      ),
    },
    {
      key: "builtin",
      header: "",
      cell: (row) =>
        row.builtin ? (
          <Badge variant="secondary" className="text-[10px]">
            Estándar
          </Badge>
        ) : null,
    },
    {
      key: "is_active",
      header: "Estado",
      cell: (row) =>
        row.is_active ? (
          <Badge variant="success">Activa</Badge>
        ) : (
          <Badge variant="secondary">Inactiva</Badge>
        ),
    },
  ];
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function ConsentTemplatesPage() {
  const { data: templates, isLoading, isError } = useConsentTemplates();
  const columns = buildColumns();

  if (isLoading) {
    return <ConsentTemplatesListSkeleton />;
  }

  if (isError) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Error al cargar plantillas"
        description="No se pudieron cargar las plantillas de consentimiento. Intenta de nuevo."
      />
    );
  }

  const isEmpty = !templates || templates.length === 0;

  return (
    <div className="space-y-6">
      {/* ─── Page Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Plantillas de consentimiento
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Administra las plantillas de consentimiento informado de la clínica.
          </p>
        </div>
        <Button asChild>
          <Link href="/settings/consent-templates/new">
            <FilePlus className="mr-2 h-4 w-4" />
            Nueva plantilla
          </Link>
        </Button>
      </div>

      {/* ─── Table or Empty State ────────────────────────────────────────── */}
      {isEmpty ? (
        <EmptyState
          icon={FileText}
          title="Sin plantillas"
          description="No hay plantillas de consentimiento. Crea la primera para poder generar consentimientos."
          action={{
            label: "Nueva plantilla",
            href: "/settings/consent-templates/new",
          }}
        />
      ) : (
        <DataTable<ConsentTemplateResponse>
          columns={columns}
          data={templates}
          loading={isLoading}
          skeletonRows={6}
          rowKey="id"
          emptyMessage="No hay plantillas de consentimiento."
        />
      )}
    </div>
  );
}
