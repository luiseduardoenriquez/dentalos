"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FilePlus, FileText, AlertCircle, Search, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import {
  useConsentTemplates,
  useDeleteConsentTemplate,
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

// ─── Category Options ────────────────────────────────────────────────────────

const CATEGORY_OPTIONS = [
  { value: "all", label: "Todas" },
  { value: "general", label: "General" },
  { value: "surgery", label: "Cirugía" },
  { value: "sedation", label: "Sedación" },
  { value: "orthodontics", label: "Ortodoncia" },
  { value: "implants", label: "Implantes" },
  { value: "endodontics", label: "Endodoncia" },
  { value: "pediatric", label: "Pediátrico" },
];

// ─── Column Definitions ──────────────────────────────────────────────────────

function buildColumns(
  onEdit: (id: string) => void,
  onDelete: (template: ConsentTemplateResponse) => void,
): ColumnDef<ConsentTemplateResponse>[] {
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
    {
      key: "actions",
      header: "",
      cell: (row) =>
        !row.builtin ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                <MoreHorizontal className="h-4 w-4" />
                <span className="sr-only">Acciones</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit(row.id)}>
                <Pencil className="mr-2 h-3.5 w-3.5" />
                Editar
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => onDelete(row)}
              >
                <Trash2 className="mr-2 h-3.5 w-3.5" />
                Eliminar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null,
    },
  ];
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function ConsentTemplatesPage() {
  const router = useRouter();
  const { data: templates, isLoading, isError } = useConsentTemplates();
  const { mutate: deleteTemplate, isPending: isDeleting } = useDeleteConsentTemplate();

  const [search, setSearch] = React.useState("");
  const [categoryFilter, setCategoryFilter] = React.useState("all");
  const [deleteTarget, setDeleteTarget] = React.useState<ConsentTemplateResponse | null>(null);

  function handleEdit(id: string) {
    router.push(`/settings/consent-templates/${id}/editar`);
  }

  function handleDeleteConfirm() {
    if (!deleteTarget) return;
    deleteTemplate(deleteTarget.id, {
      onSuccess: () => setDeleteTarget(null),
    });
  }

  const columns = buildColumns(handleEdit, setDeleteTarget);

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

  // Client-side filtering
  const filtered = (templates ?? []).filter((t) => {
    const matchesSearch =
      !search || t.name.toLowerCase().includes(search.toLowerCase());
    const matchesCategory =
      categoryFilter === "all" || t.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

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

      {/* ─── Filters ──────────────────────────────────────────────────────── */}
      {!isEmpty && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[hsl(var(--muted-foreground))]" />
            <Input
              placeholder="Buscar plantilla..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[180px]" aria-label="Filtrar por categoría">
              <SelectValue placeholder="Categoría" />
            </SelectTrigger>
            <SelectContent>
              {CATEGORY_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

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
          data={filtered}
          loading={isLoading}
          skeletonRows={6}
          rowKey="id"
          emptyMessage="No hay plantillas que coincidan con los filtros."
        />
      )}

      {/* ─── Delete Confirmation Dialog ──────────────────────────────────── */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar plantilla</AlertDialogTitle>
            <AlertDialogDescription>
              ¿Estás seguro de que deseas eliminar la plantilla &quot;{deleteTarget?.name}&quot;?
              Esta acción desactivará la plantilla y no se podrá usar para nuevos consentimientos.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? "Eliminando..." : "Eliminar"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
