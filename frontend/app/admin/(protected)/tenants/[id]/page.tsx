"use client";

/**
 * Admin tenant detail page — /admin/tenants/[id].
 *
 * Uses the dedicated GET /admin/tenants/{id} endpoint via useAdminTenantDetail(id).
 * Displays all TenantDetailResponse fields in organized Card sections.
 *
 * Actions available:
 * - Editar: opens a Dialog to update name and plan.
 * - Suspender/Reactivar: opens a confirmation Dialog to toggle suspension.
 * - Impersonar Clinica: existing impersonation flow (audit-logged).
 */

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, AlertTriangle, Pencil, ShieldOff, ShieldCheck } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
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
  useAdminTenantDetail,
  useUpdateTenant,
  useSuspendTenant,
  useAdminPlans,
  useImpersonateTenant,
  type TenantDetailResponse,
  type PlanResponse,
} from "@/lib/hooks/use-admin";
import { useImpersonationStore } from "@/lib/hooks/use-impersonation";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
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

// ─── Info Grid Item ───────────────────────────────────────────────────────────

function InfoItem({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-foreground break-all">{children}</dd>
    </div>
  );
}

// ─── JSON Display ─────────────────────────────────────────────────────────────

function JsonDisplay({ value }: { value: Record<string, unknown> }) {
  const isEmpty = Object.keys(value).length === 0;
  if (isEmpty) {
    return <span className="text-muted-foreground italic text-xs">vacío</span>;
  }
  return (
    <pre className="mt-1 text-xs font-mono bg-muted rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

// ─── Edit Dialog ──────────────────────────────────────────────────────────────

interface EditDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenant: TenantDetailResponse;
  plans: PlanResponse[];
  onSuccess: () => void;
}

function EditDialog({
  open,
  onOpenChange,
  tenant,
  plans,
  onSuccess,
}: EditDialogProps) {
  const [name, setName] = useState(tenant.name);
  const [planId, setPlanId] = useState(tenant.plan_id);
  const { mutate: updateTenant, isPending, error } = useUpdateTenant();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: { name?: string; plan_id?: string } = {};
    if (name.trim() !== tenant.name) payload.name = name.trim();
    if (planId !== tenant.plan_id) payload.plan_id = planId;

    if (Object.keys(payload).length === 0) {
      onOpenChange(false);
      return;
    }

    updateTenant(
      { id: tenant.id, payload },
      {
        onSuccess: () => {
          toast.success("Clinica actualizada correctamente.");
          onOpenChange(false);
          onSuccess();
        },
        onError: (err) => {
          toast.error(
            err instanceof Error
              ? err.message
              : "No se pudo actualizar la clinica.",
          );
        },
      },
    );
  }

  const errorMessage =
    error instanceof Error
      ? error.message
      : error
        ? "No se pudo actualizar la clinica. Intentalo de nuevo."
        : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Editar clinica</DialogTitle>
          <DialogDescription>
            Actualiza el nombre o el plan de <strong>{tenant.name}</strong>.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-name">Nombre</Label>
            <Input
              id="edit-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nombre de la clinica"
              required
              minLength={2}
              maxLength={100}
              disabled={isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-plan">Plan</Label>
            <Select value={planId} onValueChange={setPlanId} disabled={isPending}>
              <SelectTrigger id="edit-plan">
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

          {errorMessage && (
            <p className="text-sm text-destructive">{errorMessage}</p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Guardando..." : "Guardar cambios"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Suspend/Reactivate Dialog ────────────────────────────────────────────────

interface SuspendDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenant: TenantDetailResponse;
  onSuccess: () => void;
}

function SuspendDialog({
  open,
  onOpenChange,
  tenant,
  onSuccess,
}: SuspendDialogProps) {
  const isSuspended = tenant.status === "suspended";
  const { mutate: suspendTenant, isPending, error } = useSuspendTenant();

  function handleConfirm() {
    suspendTenant(tenant.id, {
      onSuccess: () => {
        toast.success(
          isSuspended
            ? "Clinica reactivada correctamente."
            : "Clinica suspendida correctamente.",
        );
        onOpenChange(false);
        onSuccess();
      },
      onError: (err) => {
        toast.error(
          err instanceof Error
            ? err.message
            : "No se pudo completar la operacion. Intentalo de nuevo.",
        );
      },
    });
  }

  const errorMessage =
    error instanceof Error
      ? error.message
      : error
        ? "No se pudo completar la operacion."
        : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isSuspended ? "Reactivar clinica" : "Suspender clinica"}
          </DialogTitle>
          <DialogDescription>
            {isSuspended
              ? `Vas a reactivar "${tenant.name}". Los usuarios podran volver a acceder.`
              : `Vas a suspender "${tenant.name}". Los usuarios no podran acceder hasta que se reactive.`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex gap-3 rounded-md border border-destructive/30 bg-destructive/5 p-3">
            <AlertTriangle
              className="h-4 w-4 text-destructive shrink-0 mt-0.5"
              aria-hidden="true"
            />
            <p className="text-sm text-destructive leading-relaxed">
              {isSuspended
                ? "Al reactivar, todos los usuarios y sus accesos seran restaurados de inmediato."
                : "Al suspender, todos los usuarios activos seran desconectados y no podran iniciar sesion."}
              {" "}Esta accion quedara registrada en el log de auditoria.
            </p>
          </div>

          {errorMessage && (
            <p className="text-sm text-destructive">{errorMessage}</p>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            variant={isSuspended ? "default" : "destructive"}
            onClick={handleConfirm}
            disabled={isPending}
          >
            {isPending
              ? "Procesando..."
              : isSuspended
                ? "Reactivar"
                : "Suspender"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Impersonation Dialog ─────────────────────────────────────────────────────

interface ImpersonationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenant: TenantDetailResponse;
}

function ImpersonationDialog({
  open,
  onOpenChange,
  tenant,
}: ImpersonationDialogProps) {
  const router = useRouter();
  const { enter } = useImpersonationStore();
  const { mutate: impersonate, isPending, error } = useImpersonateTenant();

  function handleConfirm() {
    impersonate(tenant.id, {
      onSuccess: (data) => {
        enter(data.access_token, `/admin/tenants/${tenant.id}`);
        router.push("/dashboard");
      },
    });
  }

  const errorMessage =
    error instanceof Error
      ? error.message
      : error
        ? "No se pudo iniciar la impersonacion. Intentalo de nuevo."
        : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Impersonar clinica</DialogTitle>
          <DialogDescription>
            {`Vas a acceder a "${tenant.name}" como administrador.`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex gap-3 rounded-md border border-amber-200 bg-amber-50 dark:border-amber-700/40 dark:bg-amber-900/20 p-3">
            <AlertTriangle
              className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5"
              aria-hidden="true"
            />
            <p className="text-sm text-amber-800 dark:text-amber-300 leading-relaxed">
              Vas a acceder a esta clinica como{" "}
              <strong>clinic_owner</strong>. Todas las acciones realizadas
              durante la sesion seran registradas en el log de auditoria con
              tu identidad de superadmin.
            </p>
          </div>

          {errorMessage && (
            <p className="text-sm text-destructive">{errorMessage}</p>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={isPending}
            className="bg-amber-600 hover:bg-amber-700 text-white dark:bg-amber-600 dark:hover:bg-amber-700"
          >
            {isPending ? "Redirigiendo..." : "Iniciar Impersonacion"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function TenantDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Skeleton className="h-8 w-64 mb-3" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
      </div>

      {/* Cards */}
      {Array.from({ length: 5 }).map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-5 w-40" />
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j}>
                  <Skeleton className="h-3 w-20 mb-2" />
                  <Skeleton className="h-4 w-36" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      {/* Actions card */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48 mb-2" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Skeleton className="h-9 w-28" />
            <Skeleton className="h-9 w-32" />
            <Skeleton className="h-9 w-40" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Not Found ────────────────────────────────────────────────────────────────

function TenantNotFound({ id }: { id: string }) {
  return (
    <div className="space-y-6">
      <Button asChild variant="outline" size="sm">
        <Link href="/admin/tenants">
          <ArrowLeft className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
          Volver a clinicas
        </Link>
      </Button>
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-sm font-medium text-foreground">
            Clinica no encontrada
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            No se encontro ninguna clinica con el ID{" "}
            <code className="font-mono text-xs">{id}</code>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Detail View ──────────────────────────────────────────────────────────────

interface TenantDetailProps {
  tenant: TenantDetailResponse;
  plans: PlanResponse[];
  onRefetch: () => void;
}

function TenantDetail({ tenant, plans, onRefetch }: TenantDetailProps) {
  const [editOpen, setEditOpen] = useState(false);
  const [suspendOpen, setSuspendOpen] = useState(false);
  const [impersonateOpen, setImpersonateOpen] = useState(false);

  const isSuspended = tenant.status === "suspended";

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{tenant.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={tenant.status} />
            <PlanBadge plan={tenant.plan_name} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setEditOpen(true)}
          >
            <Pencil className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
            Editar
          </Button>
          <Button
            type="button"
            variant={isSuspended ? "default" : "outline"}
            size="sm"
            onClick={() => setSuspendOpen(true)}
          >
            {isSuspended ? (
              <>
                <ShieldCheck className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
                Reactivar
              </>
            ) : (
              <>
                <ShieldOff className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
                Suspender
              </>
            )}
          </Button>
        </div>
      </div>

      {/* ── General ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Informacion general</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5">
            <InfoItem label="Nombre">{tenant.name}</InfoItem>
            <InfoItem label="Slug">
              <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
                {tenant.slug}
              </code>
            </InfoItem>
            <InfoItem label="Schema">
              <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
                {tenant.schema_name}
              </code>
            </InfoItem>
            <InfoItem label="ID">
              <code className="text-xs font-mono text-muted-foreground">
                {tenant.id}
              </code>
            </InfoItem>
            <InfoItem label="Estado">
              <StatusBadge status={tenant.status} />
            </InfoItem>
            <InfoItem label="Paso de onboarding">
              {tenant.onboarding_step}
            </InfoItem>
            <InfoItem label="Usuarios">{tenant.user_count}</InfoItem>
          </dl>
        </CardContent>
      </Card>

      {/* ── Contact ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Contacto</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5">
            <InfoItem label="Correo del propietario">
              {tenant.owner_email}
            </InfoItem>
            <InfoItem label="ID del propietario">
              {tenant.owner_user_id ? (
                <code className="text-xs font-mono text-muted-foreground">
                  {tenant.owner_user_id}
                </code>
              ) : (
                <span className="text-muted-foreground italic">—</span>
              )}
            </InfoItem>
            <InfoItem label="Telefono">
              {tenant.phone ?? <span className="text-muted-foreground italic">—</span>}
            </InfoItem>
            <InfoItem label="Direccion">
              {tenant.address ?? <span className="text-muted-foreground italic">—</span>}
            </InfoItem>
          </dl>
        </CardContent>
      </Card>

      {/* ── Plan & Locale ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Plan y configuracion regional</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5">
            <InfoItem label="Plan">
              <PlanBadge plan={tenant.plan_name} />
            </InfoItem>
            <InfoItem label="ID del plan">
              <code className="text-xs font-mono text-muted-foreground">
                {tenant.plan_id}
              </code>
            </InfoItem>
            <InfoItem label="Moneda">{tenant.currency_code}</InfoItem>
            <InfoItem label="Pais">{tenant.country_code}</InfoItem>
            <InfoItem label="Zona horaria">{tenant.timezone}</InfoItem>
            <InfoItem label="Locale">{tenant.locale}</InfoItem>
          </dl>
        </CardContent>
      </Card>

      {/* ── Config ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuracion avanzada</CardTitle>
          <CardDescription>
            Ajustes y addons del tenant en formato JSON.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Settings
            </p>
            <JsonDisplay value={tenant.settings} />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Addons
            </p>
            <JsonDisplay value={tenant.addons} />
          </div>
        </CardContent>
      </Card>

      {/* ── Dates ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fechas</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5">
            <InfoItem label="Creado">{formatDateTime(tenant.created_at)}</InfoItem>
            <InfoItem label="Actualizado">{formatDateTime(tenant.updated_at)}</InfoItem>
            <InfoItem label="Fin de trial">{formatDate(tenant.trial_ends_at)}</InfoItem>
            <InfoItem label="Suspendido el">{formatDateTime(tenant.suspended_at)}</InfoItem>
            <InfoItem label="Cancelado el">{formatDateTime(tenant.cancelled_at)}</InfoItem>
          </dl>
        </CardContent>
      </Card>

      {/* ── Admin Actions ── */}
      <Card className="border-amber-200 dark:border-amber-700/40">
        <CardHeader>
          <CardTitle className="text-base">Acciones de administrador</CardTitle>
          <CardDescription>
            Estas acciones son sensibles y quedan registradas en el log de auditoria.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              type="button"
              onClick={() => setImpersonateOpen(true)}
              className="bg-amber-600 hover:bg-amber-700 text-white dark:bg-amber-600 dark:hover:bg-amber-700"
            >
              Impersonar Clinica
            </Button>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            La impersonacion te permite acceder a la clinica con el rol
            clinic_owner. El acceso es de corta duracion y queda registrado.
          </p>
        </CardContent>
      </Card>

      {/* ── Dialogs ── */}
      <EditDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        tenant={tenant}
        plans={plans}
        onSuccess={onRefetch}
      />
      <SuspendDialog
        open={suspendOpen}
        onOpenChange={setSuspendOpen}
        tenant={tenant}
        onSuccess={onRefetch}
      />
      <ImpersonationDialog
        open={impersonateOpen}
        onOpenChange={setImpersonateOpen}
        tenant={tenant}
      />
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Tenant detail page — /admin/tenants/[id].
 *
 * Uses the dedicated GET /admin/tenants/{id} endpoint via useAdminTenantDetail.
 * Plans are pre-fetched so the edit dialog renders without a secondary loading state.
 */
export default function AdminTenantDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  // Next.js 15+ params is a Promise — use `use()` to unwrap synchronously.
  const { id } = use(params);

  const {
    data: tenant,
    isLoading,
    isError,
    refetch,
  } = useAdminTenantDetail(id);

  const { data: plans = [] } = useAdminPlans();

  return (
    <div className="space-y-6">
      {/* ── Back link ── */}
      <Button asChild variant="outline" size="sm">
        <Link href="/admin/tenants">
          <ArrowLeft className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
          Volver a clinicas
        </Link>
      </Button>

      {/* ── Error state ── */}
      {isError && (
        <Card className="border-destructive/30">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">
              No se pudo cargar la informacion de la clinica.
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

      {/* ── Loading ── */}
      {isLoading && <TenantDetailSkeleton />}

      {/* ── Content ── */}
      {!isLoading && !isError && tenant && (
        <TenantDetail
          tenant={tenant}
          plans={plans}
          onRefetch={refetch}
        />
      )}

      {/* ── Not found — API returned but tenant is undefined (should not happen with dedicated endpoint, but guard anyway) ── */}
      {!isLoading && !isError && !tenant && (
        <TenantNotFound id={id} />
      )}
    </div>
  );
}
