"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Pagination } from "@/components/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Plus, Search, BookOpen, Pencil } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CatalogItem {
  id: string;
  cups_code: string;
  name: string;
  description: string | null;
  category: string;
  default_price_cents: number;
  is_active: boolean;
}

interface CatalogListResponse {
  items: CatalogItem[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Edit / Create Dialog ─────────────────────────────────────────────────────

function CatalogItemDialog({
  open,
  onOpenChange,
  item,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: CatalogItem | null;
  onSaved: () => void;
}) {
  const { success, error: toastError } = useToast();
  const [cupsCode, setCupsCode] = React.useState("");
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [priceCents, setPriceCents] = React.useState("");

  // Populate form when editing an existing item
  React.useEffect(() => {
    if (item) {
      setCupsCode(item.cups_code);
      setName(item.name);
      setDescription(item.description ?? "");
      setCategory(item.category);
      setPriceCents(String(item.default_price_cents / 100));
    } else {
      setCupsCode("");
      setName("");
      setDescription("");
      setCategory("");
      setPriceCents("");
    }
  }, [item, open]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        cups_code: cupsCode,
        name,
        description: description || null,
        category,
        default_price_cents: Math.round(Number(priceCents) * 100),
      };
      if (item) {
        return apiPut(`/catalog/services/${item.id}`, payload);
      }
      return apiPost("/catalog/services", payload);
    },
    onSuccess: () => {
      success(item ? "Servicio actualizado" : "Servicio creado", "");
      onOpenChange(false);
      onSaved();
    },
    onError: () => {
      toastError("Error", "No se pudo guardar el servicio.");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{item ? "Editar servicio" : "Nuevo servicio"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="cups_code">Código CUPS</Label>
              <Input
                id="cups_code"
                value={cupsCode}
                onChange={(e) => setCupsCode(e.target.value)}
                placeholder="123456"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="category">Categoría</Label>
              <Input
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="Operatoria"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="name">Nombre del servicio</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Obturación con resina"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="description">Descripción (opcional)</Label>
            <Input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="price">Precio (COP)</Label>
            <Input
              id="price"
              type="number"
              value={priceCents}
              onChange={(e) => setPriceCents(e.target.value)}
              placeholder="150000"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? "Guardando..." : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CatalogManagementPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = React.useState("");
  const [debouncedSearch, setDebouncedSearch] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingItem, setEditingItem] = React.useState<CatalogItem | null>(null);

  // Debounce search input to avoid firing on every keystroke
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, isLoading } = useQuery({
    queryKey: ["catalog_services", page, debouncedSearch],
    queryFn: () =>
      apiGet<CatalogListResponse>(
        `/catalog/services?page=${page}&page_size=20${
          debouncedSearch ? `&search=${encodeURIComponent(debouncedSearch)}` : ""
        }`
      ),
    staleTime: 30_000,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  function handleEdit(item: CatalogItem) {
    setEditingItem(item);
    setDialogOpen(true);
  }

  function handleCreate() {
    setEditingItem(null);
    setDialogOpen(true);
  }

  function handleSaved() {
    queryClient.invalidateQueries({ queryKey: ["catalog_services"] });
  }

  const columns: ColumnDef<CatalogItem>[] = [
    {
      key: "cups_code",
      header: "CUPS",
      cell: (row) => (
        <Badge variant="outline" className="font-mono text-xs">
          {row.cups_code}
        </Badge>
      ),
    },
    {
      key: "name",
      header: "Nombre",
      cell: (row) => <span className="font-medium text-sm">{row.name}</span>,
    },
    {
      key: "category",
      header: "Categoría",
      cell: (row) => (
        <span className="text-sm text-[hsl(var(--muted-foreground))]">{row.category}</span>
      ),
    },
    {
      key: "default_price_cents",
      header: "Precio",
      cell: (row) => (
        <span className="text-sm font-semibold">{formatCurrency(row.default_price_cents)}</span>
      ),
    },
    {
      key: "is_active",
      header: "Estado",
      cell: (row) =>
        row.is_active ? (
          <Badge variant="success" className="text-xs">
            Activo
          </Badge>
        ) : (
          <Badge variant="secondary" className="text-xs">
            Inactivo
          </Badge>
        ),
    },
    {
      key: "actions",
      header: "",
      cell: (row) => (
        <Button variant="ghost" size="sm" onClick={() => handleEdit(row)}>
          <Pencil className="h-3.5 w-3.5" />
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Catálogo de servicios
          </h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
            Administra los procedimientos y precios de la clínica.
          </p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo servicio
        </Button>
      </div>

      {/* Search bar */}
      <div className="relative w-full sm:max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[hsl(var(--muted-foreground))]" />
        <Input
          placeholder="Buscar por nombre o código CUPS..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Empty state when catalog is completely empty and no active search */}
      {!isLoading && total === 0 && !debouncedSearch ? (
        <EmptyState
          icon={BookOpen}
          title="Catálogo vacío"
          description="Agrega el primer servicio o procedimiento al catálogo."
          action={{ label: "Agregar servicio", onClick: handleCreate }}
        />
      ) : (
        <>
          <DataTable<CatalogItem>
            columns={columns}
            data={items}
            loading={isLoading}
            skeletonRows={8}
            rowKey="id"
          />
          {total > 0 && (
            <Pagination
              page={page}
              pageSize={20}
              total={total}
              onChange={setPage}
              className="mt-4"
            />
          )}
        </>
      )}

      {/* Create / Edit dialog */}
      <CatalogItemDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        item={editingItem}
        onSaved={handleSaved}
      />
    </div>
  );
}
