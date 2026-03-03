"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Building2, Plus, AlertCircle } from "lucide-react";
import { formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Convenio {
  id: string;
  company_name: string;
  discount_type: "percentage" | "fixed";
  discount_value: number;
  valid_from: string;
  valid_until: string | null;
  is_active: boolean;
  created_at: string;
}

interface ConvenioListResponse {
  items: Convenio[];
  total: number;
  page: number;
  page_size: number;
}

interface ConvenioCreatePayload {
  company_name: string;
  discount_type: "percentage" | "fixed";
  discount_value: number;
  valid_from: string;
  valid_until?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isConvenioActive(c: Convenio): boolean {
  if (!c.is_active) return false;
  const now = new Date();
  const from = new Date(c.valid_from);
  if (now < from) return false;
  if (c.valid_until && now > new Date(c.valid_until)) return false;
  return true;
}

function discountLabel(c: Convenio): string {
  if (c.discount_type === "percentage") return `${c.discount_value}%`;
  return `$${c.discount_value.toLocaleString("es-CO")}`;
}

// ─── Create Convenio Dialog ───────────────────────────────────────────────────

function CreateConvenioDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();

  const [form, setForm] = React.useState<ConvenioCreatePayload>({
    company_name: "",
    discount_type: "percentage",
    discount_value: 10,
    valid_from: new Date().toISOString().split("T")[0],
    valid_until: "",
  });

  const { mutate: createConvenio, isPending } = useMutation({
    mutationFn: (payload: ConvenioCreatePayload) =>
      apiPost<Convenio>("/convenios", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["convenios"] });
      setForm({
        company_name: "",
        discount_type: "percentage",
        discount_value: 10,
        valid_from: new Date().toISOString().split("T")[0],
        valid_until: "",
      });
      onClose();
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    createConvenio({
      ...form,
      valid_until: form.valid_until || undefined,
    });
  }

  function update(field: keyof ConvenioCreatePayload, value: string | number) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent size="default">
        <DialogHeader>
          <DialogTitle>Nuevo convenio empresarial</DialogTitle>
          <DialogDescription>
            Registra un acuerdo de descuento con una empresa o entidad.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="company-name">Nombre de la empresa</Label>
            <Input
              id="company-name"
              placeholder="Ej: Empresa ABC S.A.S."
              value={form.company_name}
              onChange={(e) => update("company_name", e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="discount-type">Tipo de descuento</Label>
              <select
                id="discount-type"
                value={form.discount_type}
                onChange={(e) =>
                  update("discount_type", e.target.value as "percentage" | "fixed")
                }
                className={cn(
                  "w-full rounded-md border border-[hsl(var(--border))]",
                  "bg-[hsl(var(--background))] px-3 py-2 text-sm text-foreground",
                  "focus:outline-none focus:ring-2 focus:ring-primary-600",
                )}
              >
                <option value="percentage">Porcentaje (%)</option>
                <option value="fixed">Valor fijo ($)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="discount-value">
                {form.discount_type === "percentage" ? "Porcentaje" : "Valor (COP)"}
              </Label>
              <Input
                id="discount-value"
                type="number"
                min={0}
                max={form.discount_type === "percentage" ? 100 : undefined}
                value={form.discount_value}
                onChange={(e) =>
                  update("discount_value", parseFloat(e.target.value) || 0)
                }
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="valid-from">Válido desde</Label>
              <Input
                id="valid-from"
                type="date"
                value={form.valid_from}
                onChange={(e) => update("valid_from", e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="valid-until">
                Válido hasta{" "}
                <span className="text-[hsl(var(--muted-foreground))] font-normal">
                  (opcional)
                </span>
              </Label>
              <Input
                id="valid-until"
                type="date"
                value={form.valid_until}
                onChange={(e) => update("valid_until", e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending || !form.company_name.trim()}>
              {isPending ? "Guardando..." : "Crear convenio"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ConveniosPage() {
  const [createOpen, setCreateOpen] = React.useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["convenios"],
    queryFn: () => apiGet<ConvenioListResponse>("/convenios"),
    staleTime: 2 * 60_000,
  });

  const convenios = data?.items ?? [];

  return (
    <div className="space-y-6">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Convenios empresariales
          </h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Gestiona acuerdos de descuento con empresas y entidades.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo convenio
        </Button>
      </div>

      {/* ─── Table Card ──────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary-600" />
            Convenios registrados
          </CardTitle>
          <CardDescription>
            {data?.total ?? 0} convenio{data?.total !== 1 ? "s" : ""} en total
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 rounded-md" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
              <AlertCircle className="h-8 w-8 text-red-500" />
              <p className="text-sm text-red-600 dark:text-red-400">
                Error al cargar los convenios.
              </p>
            </div>
          ) : convenios.length === 0 ? (
            <div className="py-12 text-center space-y-3">
              <Building2 className="mx-auto h-10 w-10 text-[hsl(var(--muted-foreground))]" />
              <p className="text-sm font-medium text-foreground">
                No hay convenios registrados
              </p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                Crea el primer convenio con una empresa o entidad.
              </p>
              <Button variant="outline" size="sm" onClick={() => setCreateOpen(true)}>
                <Plus className="mr-2 h-3.5 w-3.5" />
                Crear primer convenio
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Empresa</TableHead>
                  <TableHead>Descuento</TableHead>
                  <TableHead>Válido desde</TableHead>
                  <TableHead>Válido hasta</TableHead>
                  <TableHead>Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {convenios.map((c) => {
                  const active = isConvenioActive(c);
                  return (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium text-foreground">
                        {c.company_name}
                      </TableCell>
                      <TableCell className="text-sm">
                        <span className="font-semibold text-primary-600">
                          {discountLabel(c)}
                        </span>{" "}
                        <span className="text-[hsl(var(--muted-foreground))]">
                          {c.discount_type === "percentage" ? "de descuento" : "fijo"}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {formatDate(c.valid_from)}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {c.valid_until ? formatDate(c.valid_until) : "Sin vencimiento"}
                      </TableCell>
                      <TableCell>
                        {active ? (
                          <Badge variant="success">Activo</Badge>
                        ) : (
                          <Badge variant="secondary">Expirado</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ─── Dialog ──────────────────────────────────────────────────────── */}
      <CreateConvenioDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
