"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronRight, RefreshCw, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useInventoryItem,
  useUpdateInventoryItem,
  type QuantityChangeReason,
} from "@/lib/hooks/use-inventory";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  material: "Material",
  instrument: "Instrumento",
  implant: "Implante",
  medication: "Medicamento",
};

const UNIT_LABELS: Record<string, string> = {
  units: "Unidades",
  ml: "mL",
  g: "g",
  boxes: "Cajas",
};

const CHANGE_REASON_OPTIONS: { value: QuantityChangeReason; label: string }[] = [
  { value: "received", label: "Recibido" },
  { value: "consumed", label: "Consumido" },
  { value: "discarded", label: "Descartado" },
  { value: "adjustment", label: "Ajuste" },
];

// ─── Expiry Badge ─────────────────────────────────────────────────────────────

function ExpiryBadge({ status }: { status: string | null }) {
  if (!status) return null;

  const config: Record<string, { label: string; className: string }> = {
    ok: {
      label: "Vigente",
      className:
        "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-700",
    },
    warning: {
      label: "Por vencer (próximos 90 días)",
      className:
        "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-700",
    },
    critical: {
      label: "Por vencer (próximos 30 días)",
      className:
        "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:border-orange-700",
    },
    expired: {
      label: "Vencido",
      className:
        "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-700",
    },
  };

  const { label, className } = config[status] ?? {
    label: status,
    className: "",
  };

  return (
    <Badge variant="outline" className={cn("text-xs font-medium", className)}>
      {label}
    </Badge>
  );
}

// ─── Info Row ─────────────────────────────────────────────────────────────────

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:items-center sm:justify-between py-2.5 border-b border-[hsl(var(--border))] last:border-0">
      <span className="text-sm text-[hsl(var(--muted-foreground))]">{label}</span>
      <span className="text-sm font-medium text-foreground">{value ?? "—"}</span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InventoryItemDetailPage() {
  const params = useParams<{ id: string }>();
  const itemId = params.id;

  const { data: item, isLoading } = useInventoryItem(itemId);
  const updateMutation = useUpdateInventoryItem(itemId);

  // Stock adjustment form state
  const [quantityChange, setQuantityChange] = React.useState("");
  const [changeReason, setChangeReason] = React.useState<QuantityChangeReason>("received");
  const [changeNotes, setChangeNotes] = React.useState("");

  function handleAdjustStock(e: React.FormEvent) {
    e.preventDefault();
    const delta = Number(quantityChange);
    if (isNaN(delta) || delta === 0) return;

    updateMutation.mutate(
      {
        quantity_change: delta,
        change_reason: changeReason,
        change_notes: changeNotes.trim() || undefined,
      },
      {
        onSuccess: () => {
          setQuantityChange("");
          setChangeNotes("");
          setChangeReason("received");
        },
      },
    );
  }

  // ─── Loading ──────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--muted-foreground))]" />
      </div>
    );
  }

  if (!item) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20 text-[hsl(var(--muted-foreground))]">
        <AlertCircle className="h-10 w-10 opacity-40" />
        <p className="text-sm">Artículo no encontrado.</p>
        <Button variant="outline" size="sm" asChild>
          <Link href="/inventory">Volver al inventario</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* ─── Breadcrumb ─────────────────────────────────────────────────── */}
      <nav
        className="flex items-center gap-1.5 text-sm text-[hsl(var(--muted-foreground))]"
        aria-label="Ruta de navegación"
      >
        <Link href="/inventory" className="hover:text-foreground transition-colors">
          Inventario
        </Link>
        <ChevronRight className="h-4 w-4" />
        <span className="text-foreground font-medium truncate max-w-[220px]">
          {item.name}
        </span>
      </nav>

      {/* ─── Item Info Card ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <CardTitle className="text-xl">{item.name}</CardTitle>
              <CardDescription className="mt-1">
                <Badge variant="outline" className="text-xs">
                  {CATEGORY_LABELS[item.category] ?? item.category}
                </Badge>
              </CardDescription>
            </div>
            {item.expiry_status && (
              <ExpiryBadge status={item.expiry_status} />
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-[hsl(var(--border))]">
            <InfoRow
              label="Cantidad actual"
              value={
                <span className="tabular-nums">
                  {item.quantity}{" "}
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    {UNIT_LABELS[item.unit] ?? item.unit}
                  </span>
                </span>
              }
            />
            <InfoRow label="Stock mínimo" value={`${item.minimum_stock} ${UNIT_LABELS[item.unit] ?? item.unit}`} />
            {item.lot_number && (
              <InfoRow label="Número de lote" value={item.lot_number} />
            )}
            {item.expiry_date && (
              <InfoRow
                label="Fecha de vencimiento"
                value={
                  <span
                    className={cn(
                      item.expiry_status === "expired" && "text-[#ef4444] font-semibold",
                      item.expiry_status === "critical" && "text-[#f97316] font-semibold",
                      item.expiry_status === "warning" && "text-[#eab308] font-semibold",
                    )}
                  >
                    {new Date(item.expiry_date).toLocaleDateString("es-CO")}
                  </span>
                }
              />
            )}
            {item.manufacturer && (
              <InfoRow label="Fabricante" value={item.manufacturer} />
            )}
            {item.supplier && (
              <InfoRow label="Proveedor" value={item.supplier} />
            )}
            {item.cost_per_unit !== null && item.cost_per_unit !== undefined && (
              <InfoRow
                label="Costo por unidad"
                value={formatCurrency(item.cost_per_unit)}
              />
            )}
            {item.location && (
              <InfoRow label="Ubicación" value={item.location} />
            )}
            <InfoRow
              label="Registrado el"
              value={formatDate(item.created_at)}
            />
          </div>
        </CardContent>
      </Card>

      {/* ─── Stock Adjustment ────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ajuste de stock</CardTitle>
          <CardDescription>
            Registra entradas, salidas o correcciones de inventario.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAdjustStock} className="flex flex-col gap-4">
            <div className="grid gap-3 sm:grid-cols-2">
              {/* Quantity change */}
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="qty-change">
                  Cantidad <span className="text-[hsl(var(--muted-foreground))] text-xs">(negativo para salidas)</span>
                </Label>
                <Input
                  id="qty-change"
                  type="number"
                  value={quantityChange}
                  onChange={(e) => setQuantityChange(e.target.value)}
                  placeholder="Ej. 10 ó -5"
                  required
                />
              </div>

              {/* Reason */}
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="change-reason">
                  Motivo <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={changeReason}
                  onValueChange={(v) => setChangeReason(v as QuantityChangeReason)}
                >
                  <SelectTrigger id="change-reason">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CHANGE_REASON_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Notes */}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="change-notes">Notas (opcional)</Label>
              <textarea
                id="change-notes"
                value={changeNotes}
                onChange={(e) => setChangeNotes(e.target.value)}
                placeholder="Descripción del ajuste..."
                rows={2}
                className={cn(
                  "flex w-full rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))]",
                  "px-3 py-2 text-sm placeholder:text-[hsl(var(--muted-foreground))]",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0",
                  "resize-none",
                )}
              />
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={
                  updateMutation.isPending ||
                  !quantityChange ||
                  Number(quantityChange) === 0
                }
              >
                {updateMutation.isPending ? "Guardando..." : "Registrar ajuste"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
