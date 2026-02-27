"use client";

import * as React from "react";
import Link from "next/link";
import { Plus, RefreshCw, Pencil, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useInventoryItems,
  useCreateInventoryItem,
  type ItemCategory,
  type ItemUnit,
  type InventoryItemCreate,
} from "@/lib/hooks/use-inventory";
import { cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const CATEGORY_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "material", label: "Material" },
  { value: "instrument", label: "Instrumento" },
  { value: "implant", label: "Implante" },
  { value: "medication", label: "Medicamento" },
];

const CATEGORY_LABELS: Record<string, string> = {
  material: "Material",
  instrument: "Instrumento",
  implant: "Implante",
  medication: "Medicamento",
};

const EXPIRY_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "Todos los estados" },
  { value: "ok", label: "Vigente" },
  { value: "warning", label: "Por vencer" },
  { value: "critical", label: "Crítico" },
  { value: "expired", label: "Vencido" },
];

const UNIT_OPTIONS: { value: ItemUnit; label: string }[] = [
  { value: "units", label: "Unidades" },
  { value: "ml", label: "mL" },
  { value: "g", label: "g" },
  { value: "boxes", label: "Cajas" },
];

// ─── Semaphore Dot ────────────────────────────────────────────────────────────

function SemaphoreDot({ status }: { status: string | null }) {
  if (!status) {
    return <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-300" />;
  }

  const colorMap: Record<string, string> = {
    ok: "bg-[#22c55e]",
    warning: "bg-[#eab308]",
    critical: "bg-[#f97316]",
    expired: "bg-[#ef4444]",
  };

  const labelMap: Record<string, string> = {
    ok: "Vigente",
    warning: "Por vencer",
    critical: "Crítico",
    expired: "Vencido",
  };

  return (
    <span
      className={cn("inline-block h-2.5 w-2.5 rounded-full", colorMap[status] ?? "bg-gray-300")}
      title={labelMap[status] ?? status}
    />
  );
}

// ─── Create Item Form ─────────────────────────────────────────────────────────

const INITIAL_FORM: InventoryItemCreate = {
  name: "",
  category: "material",
  quantity: 0,
  unit: "units",
  lot_number: "",
  expiry_date: "",
  manufacturer: "",
  supplier: "",
  cost_per_unit: undefined,
  minimum_stock: 0,
  location: "",
};

function CreateItemDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [form, setForm] = React.useState<InventoryItemCreate>(INITIAL_FORM);
  const createMutation = useCreateInventoryItem();

  function handleChange(field: keyof InventoryItemCreate, value: string | number) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    // Build payload, omitting empty optional strings
    const payload: InventoryItemCreate = {
      name: form.name.trim(),
      category: form.category,
      quantity: Number(form.quantity),
      unit: form.unit,
      minimum_stock: Number(form.minimum_stock ?? 0),
      ...(form.lot_number?.trim() && { lot_number: form.lot_number.trim() }),
      ...(form.expiry_date && { expiry_date: form.expiry_date }),
      ...(form.manufacturer?.trim() && { manufacturer: form.manufacturer.trim() }),
      ...(form.supplier?.trim() && { supplier: form.supplier.trim() }),
      ...(form.cost_per_unit !== undefined && form.cost_per_unit !== null && {
        cost_per_unit: Number(form.cost_per_unit),
      }),
      ...(form.location?.trim() && { location: form.location.trim() }),
    };

    createMutation.mutate(payload, {
      onSuccess: () => {
        setForm(INITIAL_FORM);
        onOpenChange(false);
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Nuevo artículo</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mt-2">
          {/* Name */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="item-name">
              Nombre <span className="text-red-500">*</span>
            </Label>
            <Input
              id="item-name"
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
              placeholder="Ej. Guantes de nitrilo talla M"
              required
            />
          </div>

          {/* Category + Unit row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-category">
                Categoría <span className="text-red-500">*</span>
              </Label>
              <Select
                value={form.category}
                onValueChange={(v) => handleChange("category", v as ItemCategory)}
              >
                <SelectTrigger id="item-category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORY_OPTIONS.filter((c) => c.value !== "all").map((c) => (
                    <SelectItem key={c.value} value={c.value}>
                      {c.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-unit">
                Unidad <span className="text-red-500">*</span>
              </Label>
              <Select
                value={form.unit}
                onValueChange={(v) => handleChange("unit", v as ItemUnit)}
              >
                <SelectTrigger id="item-unit">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {UNIT_OPTIONS.map((u) => (
                    <SelectItem key={u.value} value={u.value}>
                      {u.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Quantity + Min stock row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-quantity">
                Cantidad inicial <span className="text-red-500">*</span>
              </Label>
              <Input
                id="item-quantity"
                type="number"
                min={0}
                value={form.quantity}
                onChange={(e) => handleChange("quantity", e.target.value)}
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-min-stock">Stock mínimo</Label>
              <Input
                id="item-min-stock"
                type="number"
                min={0}
                value={form.minimum_stock ?? 0}
                onChange={(e) => handleChange("minimum_stock", e.target.value)}
              />
            </div>
          </div>

          {/* Lot + Expiry row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-lot">Lote</Label>
              <Input
                id="item-lot"
                value={form.lot_number ?? ""}
                onChange={(e) => handleChange("lot_number", e.target.value)}
                placeholder="Ej. LOT-2025-001"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-expiry">Fecha de vencimiento</Label>
              <Input
                id="item-expiry"
                type="date"
                value={form.expiry_date ?? ""}
                onChange={(e) => handleChange("expiry_date", e.target.value)}
              />
            </div>
          </div>

          {/* Manufacturer + Supplier row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-manufacturer">Fabricante</Label>
              <Input
                id="item-manufacturer"
                value={form.manufacturer ?? ""}
                onChange={(e) => handleChange("manufacturer", e.target.value)}
                placeholder="Ej. 3M Colombia"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-supplier">Proveedor</Label>
              <Input
                id="item-supplier"
                value={form.supplier ?? ""}
                onChange={(e) => handleChange("supplier", e.target.value)}
                placeholder="Ej. Distribuciones S.A."
              />
            </div>
          </div>

          {/* Cost + Location row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-cost">Costo por unidad (centavos COP)</Label>
              <Input
                id="item-cost"
                type="number"
                min={0}
                value={form.cost_per_unit ?? ""}
                onChange={(e) =>
                  handleChange(
                    "cost_per_unit",
                    e.target.value === "" ? "" : Number(e.target.value),
                  )
                }
                placeholder="Ej. 500000"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item-location">Ubicación</Label>
              <Input
                id="item-location"
                value={form.location ?? ""}
                onChange={(e) => handleChange("location", e.target.value)}
                placeholder="Ej. Armario A, estante 2"
              />
            </div>
          </div>

          <DialogFooter className="mt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending || !form.name.trim()}
            >
              {createMutation.isPending ? "Guardando..." : "Crear artículo"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InventoryPage() {
  const [page, setPage] = React.useState(1);
  const [category, setCategory] = React.useState("all");
  const [expiryStatus, setExpiryStatus] = React.useState("all");
  const [lowStock, setLowStock] = React.useState(false);
  const [showCreateDialog, setShowCreateDialog] = React.useState(false);

  // Reset to page 1 when filters change
  React.useEffect(() => {
    setPage(1);
  }, [category, expiryStatus, lowStock]);

  const { data, isLoading } = useInventoryItems(
    page,
    20,
    category !== "all" ? category : undefined,
    expiryStatus !== "all" ? expiryStatus : undefined,
    lowStock || undefined,
  );

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / (data?.page_size ?? 20));

  return (
    <div className="flex flex-col gap-6">
      {/* ─── Filter bar ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-end gap-3">
        {/* Category filter */}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="filter-category" className="text-xs text-[hsl(var(--muted-foreground))]">
            Categoría
          </Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger id="filter-category" className="w-44">
              <SelectValue />
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

        {/* Expiry status filter */}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="filter-expiry" className="text-xs text-[hsl(var(--muted-foreground))]">
            Estado de vencimiento
          </Label>
          <Select value={expiryStatus} onValueChange={setExpiryStatus}>
            <SelectTrigger id="filter-expiry" className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {EXPIRY_FILTER_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Low stock toggle */}
        <div className="flex items-center gap-2 pb-0.5">
          <input
            id="filter-low-stock"
            type="checkbox"
            checked={lowStock}
            onChange={(e) => setLowStock(e.target.checked)}
            className="h-4 w-4 rounded border-[hsl(var(--border))] accent-primary-600 cursor-pointer"
          />
          <Label htmlFor="filter-low-stock" className="cursor-pointer text-sm">
            Solo stock bajo
          </Label>
        </div>

        {/* Spacer + New item button */}
        <div className="ml-auto">
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo artículo
          </Button>
        </div>
      </div>

      {/* ─── Table ──────────────────────────────────────────────────────── */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-20 text-[hsl(var(--muted-foreground))]">
              <Package className="h-10 w-10 opacity-40" />
              <p className="text-sm">
                {total === 0
                  ? "No hay artículos en el inventario."
                  : "No hay artículos que coincidan con los filtros."}
              </p>
              {total === 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowCreateDialog(true)}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Agregar primer artículo
                </Button>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Categoría</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead>Vencimiento</TableHead>
                  <TableHead>Ubicación</TableHead>
                  <TableHead className="w-20">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium text-foreground">
                      {item.name}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {CATEGORY_LABELS[item.category] ?? item.category}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {item.quantity}{" "}
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">
                        {item.unit}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <SemaphoreDot status={item.expiry_status} />
                        <span className="text-sm text-[hsl(var(--muted-foreground))]">
                          {item.expiry_date
                            ? new Date(item.expiry_date).toLocaleDateString("es-CO")
                            : "—"}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                      {item.location ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/inventory/${item.id}`}>
                          <Pencil className="h-4 w-4" />
                          <span className="sr-only">Editar {item.name}</span>
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ─── Pagination ─────────────────────────────────────────────────── */}
      {total > 0 && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
          >
            Anterior
          </Button>
          <span className="text-sm text-[hsl(var(--muted-foreground))]">
            Página {page} de {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
          >
            Siguiente
          </Button>
        </div>
      )}

      {/* ─── Create dialog ──────────────────────────────────────────────── */}
      <CreateItemDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
      />
    </div>
  );
}
