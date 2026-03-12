"use client";

/**
 * Admin tenants list page.
 *
 * Features:
 * - Free-text search with 300ms debounce.
 * - Status dropdown filter: Todos / active / trial / suspended / cancelled.
 * - Plan dropdown filter: Todos los planes / dynamic list from useAdminPlans().
 * - Country dropdown filter: Todos los paises / CO / MX / PE / CL / AR.
 * - Sort dropdown: name / created_at / status.
 * - Sort order toggle button: asc / desc.
 * - Page size selector: 10 / 20 / 50.
 * - Paginated table with links to each tenant's detail page.
 * - doctor_count column alongside user_count.
 * - Previous / Next pagination controls.
 */

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, Plus, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
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
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  useAdminTenants,
  useAdminPlans,
  useCreateTenant,
  type TenantSummary,
} from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ─── Constants ─────────────────────────────────────────────────────────────────

const COUNTRY_OPTIONS: { value: string; label: string }[] = [
  { value: "CO", label: "Colombia" },
  { value: "MX", label: "Mexico" },
  { value: "PE", label: "Peru" },
  { value: "CL", label: "Chile" },
  { value: "AR", label: "Argentina" },
];

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "created_at", label: "Fecha creacion" },
  { value: "name", label: "Nombre" },
  { value: "status", label: "Estado" },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// ─── Plan Badge ───────────────────────────────────────────────────────────────

const PLAN_CLASSES: Record<string, string> = {
  free: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
  starter:
    "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700/40",
  pro: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-700/40",
  clinica:
    "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-900/30 dark:text-teal-300 dark:border-teal-700/40",
  enterprise:
    "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700/40",
};

function PlanBadge({ plan }: { plan: string }) {
  const normalized = plan.toLowerCase();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border",
        PLAN_CLASSES[normalized] ?? PLAN_CLASSES.free,
      )}
    >
      {plan}
    </span>
  );
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

const STATUS_VARIANTS: Record<string, React.ComponentProps<typeof Badge>["variant"]> = {
  active: "success",
  trial: "warning",
  suspended: "destructive",
  cancelled: "outline",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Activa",
  trial: "Trial",
  suspended: "Suspendida",
  cancelled: "Cancelada",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant={STATUS_VARIANTS[status] ?? "outline"}>
      {STATUS_LABELS[status] ?? status}
    </Badge>
  );
}

// ─── Table ────────────────────────────────────────────────────────────────────

interface TenantsTableProps {
  tenants: TenantSummary[];
  isLoading: boolean;
  pageSize: number;
}

function TenantsTable({ tenants, isLoading, pageSize }: TenantsTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" aria-label="Lista de clinicas">
        <thead>
          <tr className="border-b border-[hsl(var(--border))]">
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Nombre
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Slug
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Plan
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Estado
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Usuarios
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Doctores
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Creado
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))]">
          {isLoading
            ? Array.from({ length: pageSize > 10 ? 10 : pageSize }).map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-40" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-28" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-5 w-20 rounded-full" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-8 ml-auto" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-8 ml-auto" />
                  </td>
                  <td className="px-4 py-3">
                    <Skeleton className="h-4 w-24" />
                  </td>
                </tr>
              ))
            : tenants.map((tenant) => (
                <tr
                  key={tenant.id}
                  className="hover:bg-[hsl(var(--muted))] transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-foreground">
                    <Link
                      href={`/admin/tenants/${tenant.id}`}
                      className="hover:underline text-primary-600 dark:text-primary-400"
                    >
                      {tenant.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <code className="text-xs font-mono text-muted-foreground bg-[hsl(var(--muted))] px-1.5 py-0.5 rounded">
                      {tenant.slug}
                    </code>
                  </td>
                  <td className="px-4 py-3">
                    <PlanBadge plan={tenant.plan_name} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={tenant.status} />
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-foreground">
                    {tenant.user_count}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-foreground">
                    {tenant.doctor_count}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                    {formatDate(tenant.created_at)}
                  </td>
                </tr>
              ))}
        </tbody>
      </table>

      {!isLoading && tenants.length === 0 && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          No se encontraron clinicas con los filtros actuales.
        </p>
      )}
    </div>
  );
}

// ─── Create Tenant Dialog ─────────────────────────────────────────────────────

interface CreateTenantDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ─── Wizard Constants ─────────────────────────────────────────────────────────

const COUNTRY_DEFAULTS: Record<string, { timezone: string; currency: string }> = {
  CO: { timezone: "America/Bogota", currency: "COP" },
  MX: { timezone: "America/Mexico_City", currency: "MXN" },
  PE: { timezone: "America/Lima", currency: "PEN" },
  CL: { timezone: "America/Santiago", currency: "CLP" },
  AR: { timezone: "America/Argentina/Buenos_Aires", currency: "ARS" },
};

const WIZARD_STEPS = [
  { num: 1, label: "Basico" },
  { num: 2, label: "Plan" },
  { num: 3, label: "Config" },
];

function CreateTenantDialog({ open, onOpenChange }: CreateTenantDialogProps) {
  const router = useRouter();
  const { data: plans = [] } = useAdminPlans();
  const { mutate: createTenant, isPending } = useCreateTenant();

  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [planId, setPlanId] = useState("");
  const [countryCode, setCountryCode] = useState("CO");
  const [timezone, setTimezone] = useState("America/Bogota");
  const [currency, setCurrency] = useState("COP");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");

  function handleClose() {
    onOpenChange(false);
    setStep(1);
    setName("");
    setOwnerEmail("");
    setPlanId("");
    setCountryCode("CO");
    setTimezone("America/Bogota");
    setCurrency("COP");
    setPhone("");
    setAddress("");
  }

  function handleCountryChange(value: string) {
    setCountryCode(value);
    const defaults = COUNTRY_DEFAULTS[value];
    if (defaults) {
      setTimezone(defaults.timezone);
      setCurrency(defaults.currency);
    }
  }

  function isStep1Valid(): boolean {
    return name.trim().length >= 2 && ownerEmail.includes("@") && ownerEmail.includes(".");
  }

  function isStep2Valid(): boolean {
    return planId.trim().length > 0;
  }

  function handleNext() {
    if (step === 1 && !isStep1Valid()) {
      toast.error("Completa el nombre (min. 2 caracteres) y un correo valido.");
      return;
    }
    if (step === 2 && !isStep2Valid()) {
      toast.error("Selecciona un plan para continuar.");
      return;
    }
    setStep((s) => Math.min(3, s + 1));
  }

  function handleBack() {
    setStep((s) => Math.max(1, s - 1));
  }

  function handleCreate() {
    createTenant(
      {
        name: name.trim(),
        owner_email: ownerEmail.trim(),
        plan_id: planId,
        country_code: countryCode,
        timezone,
        currency_code: currency,
      },
      {
        onSuccess: (data) => {
          toast.success(`Clinica "${data.name}" creada correctamente.`);
          handleClose();
          router.push(`/admin/tenants/${data.id}`);
        },
        onError: (err) => {
          toast.error(
            err instanceof Error
              ? err.message
              : "No se pudo crear la clinica. Intentalo de nuevo.",
          );
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Nueva clinica</DialogTitle>
          <DialogDescription>
            Crea una nueva clinica con su esquema de base de datos.
          </DialogDescription>
        </DialogHeader>

        {/* ── Stepper ── */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {WIZARD_STEPS.map((s, i) => (
            <React.Fragment key={s.num}>
              {i > 0 && (
                <div
                  className={cn(
                    "h-px w-8",
                    step >= s.num ? "bg-indigo-500" : "bg-[hsl(var(--border))]",
                  )}
                />
              )}
              <div className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold",
                    step >= s.num
                      ? "bg-indigo-600 text-white"
                      : "bg-[hsl(var(--muted))] text-muted-foreground",
                  )}
                >
                  {s.num}
                </div>
                <span
                  className={cn(
                    "text-[10px] font-medium",
                    step >= s.num
                      ? "text-indigo-600 dark:text-indigo-400"
                      : "text-muted-foreground",
                  )}
                >
                  {s.label}
                </span>
              </div>
            </React.Fragment>
          ))}
        </div>

        {/* ── Step 1: Informacion Basica ── */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="create-name">
                Nombre de la clinica <span className="text-destructive">*</span>
              </Label>
              <Input
                id="create-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ej: Odontologia Sonrisa"
                maxLength={200}
                disabled={isPending}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-email">
                Correo del propietario <span className="text-destructive">*</span>
              </Label>
              <Input
                id="create-email"
                type="email"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                placeholder="admin@clinica.com"
                disabled={isPending}
              />
            </div>
          </div>
        )}

        {/* ── Step 2: Plan y Ubicacion ── */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="create-plan">
                Plan <span className="text-destructive">*</span>
              </Label>
              <Select value={planId} onValueChange={setPlanId} disabled={isPending}>
                <SelectTrigger id="create-plan">
                  <SelectValue placeholder="Selecciona un plan" />
                </SelectTrigger>
                <SelectContent>
                  {plans.map((plan) => (
                    <SelectItem key={plan.id} value={plan.id}>
                      {plan.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-country">Pais</Label>
              <Select value={countryCode} onValueChange={handleCountryChange} disabled={isPending}>
                <SelectTrigger id="create-country">
                  <SelectValue placeholder="Selecciona un pais" />
                </SelectTrigger>
                <SelectContent>
                  {COUNTRY_OPTIONS.map((c) => (
                    <SelectItem key={c.value} value={c.value}>
                      {c.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="create-tz">Zona horaria</Label>
                <Input
                  id="create-tz"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  placeholder="America/Bogota"
                  disabled={isPending}
                  className="text-sm"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="create-currency">Moneda</Label>
                <Input
                  id="create-currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                  placeholder="COP"
                  maxLength={3}
                  disabled={isPending}
                  className="text-sm"
                />
              </div>
            </div>
          </div>
        )}

        {/* ── Step 3: Configuracion Inicial ── */}
        {step === 3 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="create-phone">Telefono de la clinica</Label>
              <Input
                id="create-phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+57 300 000 0000"
                disabled={isPending}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-address">Direccion</Label>
              <Input
                id="create-address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Calle 123 # 45-67, Bogota"
                disabled={isPending}
              />
            </div>

            <div className="space-y-3">
              <Label className="text-sm font-medium">Add-ons disponibles</Label>
              <p className="text-xs text-muted-foreground -mt-1">
                Los add-ons se pueden activar despues desde la configuracion de la clinica.
              </p>
              <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] p-3">
                <label className="flex items-start gap-3 cursor-default">
                  <input
                    type="checkbox"
                    disabled
                    className="mt-0.5 h-4 w-4 rounded border-[hsl(var(--border))] accent-indigo-600"
                  />
                  <div>
                    <span className="text-sm font-medium">AI Voice</span>
                    <span className="ml-2 text-xs text-muted-foreground">$10/doctor/mes</span>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Dictado de voz al odontograma con Whisper + Claude.
                    </p>
                  </div>
                </label>
                <label className="flex items-start gap-3 cursor-default">
                  <input
                    type="checkbox"
                    disabled
                    className="mt-0.5 h-4 w-4 rounded border-[hsl(var(--border))] accent-indigo-600"
                  />
                  <div>
                    <span className="text-sm font-medium">AI Radiograph</span>
                    <span className="ml-2 text-xs text-muted-foreground">$20/doctor/mes</span>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Analisis automatico de radiografias con IA.
                    </p>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* ── Footer ── */}
        <DialogFooter className="mt-6 flex-row justify-between sm:justify-between gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={isPending}
          >
            Cancelar
          </Button>
          <div className="flex gap-2">
            {step > 1 && (
              <Button
                type="button"
                variant="outline"
                onClick={handleBack}
                disabled={isPending}
              >
                Anterior
              </Button>
            )}
            {step < 3 ? (
              <Button type="button" onClick={handleNext} disabled={isPending}>
                Siguiente
              </Button>
            ) : (
              <Button type="button" onClick={handleCreate} disabled={isPending}>
                {isPending ? "Creando..." : "Crear clinica"}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Admin tenants list.
 *
 * State is managed locally (no URL params for MVP):
 * - page: current page number (resets to 1 on filter change).
 * - pageSize: items per page, from 10/20/50 selector.
 * - searchInput: raw input string (not debounced).
 * - debouncedSearch: debounced version passed to the hook (300ms).
 * - statusFilter: "all" or a specific status string.
 * - planFilter: "all" or a specific plan UUID.
 * - countryFilter: "all" or a 2-letter country code.
 * - sortBy: field name to sort by (name | created_at | status).
 * - sortOrder: "asc" or "desc".
 */
export default function AdminTenantsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<10 | 20 | 50>(20);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [planFilter, setPlanFilter] = useState("all");
  const [countryFilter, setCountryFilter] = useState("all");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [createOpen, setCreateOpen] = useState(false);

  // Plans for the plan filter dropdown
  const { data: plans = [] } = useAdminPlans();

  // Debounce the search input by 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      // Reset to page 1 when search changes
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Reset page when status changes
  function handleStatusChange(value: string) {
    setStatusFilter(value);
    setPage(1);
  }

  // Reset page when plan filter changes
  function handlePlanChange(value: string) {
    setPlanFilter(value);
    setPage(1);
  }

  // Reset page when country filter changes
  function handleCountryChange(value: string) {
    setCountryFilter(value);
    setPage(1);
  }

  // Reset page when sort field changes
  function handleSortByChange(value: string) {
    setSortBy(value);
    setPage(1);
  }

  // Toggle sort order between asc and desc
  function handleSortOrderToggle() {
    setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    setPage(1);
  }

  // Reset page when page size changes
  function handlePageSizeChange(value: string) {
    setPageSize(Number(value) as 10 | 20 | 50);
    setPage(1);
  }

  const { data, isLoading, isError, refetch } = useAdminTenants({
    page,
    page_size: pageSize,
    search: debouncedSearch || undefined,
    status: statusFilter !== "all" ? statusFilter : undefined,
    planId: planFilter !== "all" ? planFilter : undefined,
    countryCode: countryFilter !== "all" ? countryFilter : undefined,
    sortBy,
    sortOrder,
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  // Resolve the current sort order icon
  const SortOrderIcon =
    sortOrder === "asc" ? ArrowUp : sortOrder === "desc" ? ArrowDown : ArrowUpDown;

  const sortOrderLabel = sortOrder === "asc" ? "Ascendente" : "Descendente";

  return (
    <div className="space-y-6">
      {/* ── Page title ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Clinicas</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {data ? `${data.total} clinicas en total` : "Listado de todas las clinicas de la plataforma"}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} size="sm">
          <Plus className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
          Nueva Clinica
        </Button>
      </div>

      {/* ── Create Dialog ── */}
      <CreateTenantDialog open={createOpen} onOpenChange={setCreateOpen} />

      {/* ── Filters — row 1: search + status + page size ── */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none"
            aria-hidden="true"
          />
          <Input
            type="search"
            placeholder="Buscar por nombre o slug..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
            aria-label="Buscar clinicas"
          />
        </div>

        {/* Status filter */}
        <Select value={statusFilter} onValueChange={handleStatusChange}>
          <SelectTrigger className="w-full sm:w-44" aria-label="Filtrar por estado">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="active">Activa</SelectItem>
            <SelectItem value="trial">Trial</SelectItem>
            <SelectItem value="suspended">Suspendida</SelectItem>
            <SelectItem value="cancelled">Cancelada</SelectItem>
          </SelectContent>
        </Select>

        {/* Page size */}
        <Select value={String(pageSize)} onValueChange={handlePageSizeChange}>
          <SelectTrigger className="w-full sm:w-28" aria-label="Elementos por pagina">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="10">10 / pag.</SelectItem>
            <SelectItem value="20">20 / pag.</SelectItem>
            <SelectItem value="50">50 / pag.</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* ── Filters — row 2: plan + country + sort ── */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Plan filter */}
        <Select value={planFilter} onValueChange={handlePlanChange}>
          <SelectTrigger className="w-full sm:w-52" aria-label="Filtrar por plan">
            <SelectValue placeholder="Todos los planes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los planes</SelectItem>
            {plans.map((plan) => (
              <SelectItem key={plan.id} value={plan.id}>
                {plan.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Country filter */}
        <Select value={countryFilter} onValueChange={handleCountryChange}>
          <SelectTrigger className="w-full sm:w-52" aria-label="Filtrar por pais">
            <SelectValue placeholder="Todos los paises" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los paises</SelectItem>
            {COUNTRY_OPTIONS.map((country) => (
              <SelectItem key={country.value} value={country.value}>
                {country.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Sort by */}
        <Select value={sortBy} onValueChange={handleSortByChange}>
          <SelectTrigger className="w-full sm:w-52" aria-label="Ordenar por">
            <SelectValue placeholder="Ordenar por" />
          </SelectTrigger>
          <SelectContent>
            {SORT_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Sort order toggle */}
        <Button
          variant="outline"
          size="default"
          onClick={handleSortOrderToggle}
          aria-label={`Orden actual: ${sortOrderLabel}. Haz clic para cambiar`}
          className="w-full sm:w-auto gap-2"
        >
          <SortOrderIcon className="h-4 w-4" aria-hidden="true" />
          <span className="text-sm">{sortOrderLabel}</span>
        </Button>
      </div>

      {/* ── Error state ── */}
      {isError && (
        <Card className="border-destructive-200 dark:border-destructive-700/40">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive-600 dark:text-destructive-400">
              No se pudo cargar la lista de clinicas.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => refetch()}
            >
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── Table ── */}
      {!isError && (
        <Card className="overflow-hidden">
          <TenantsTable
            tenants={data?.items ?? []}
            isLoading={isLoading}
            pageSize={pageSize}
          />
        </Card>
      )}

      {/* ── Pagination ── */}
      {!isError && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Pagina {page} de {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || isLoading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || isLoading}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
