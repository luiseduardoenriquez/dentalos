"use client";

/**
 * Admin tenant detail page.
 *
 * Since there is no dedicated GET /admin/tenants/{id} endpoint, this page:
 * 1. Reads the `id` param from the URL.
 * 2. Fetches the tenant list (page 1, page_size 100) and finds the matching tenant.
 * 3. If found: renders the detail grid and impersonation card.
 * 4. If not found after loading: shows a "Clinica no encontrada" state.
 *
 * Impersonation flow:
 * - User clicks "Impersonar Clinica".
 * - Confirmation dialog warns that all actions will be audit-logged.
 * - On confirm: calls POST /admin/tenants/{id}/impersonate.
 * - On success: injects the token and redirects to /dashboard.
 */

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, AlertTriangle } from "lucide-react";
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
import {
  useAdminTenants,
  useImpersonateTenant,
  type TenantSummary,
} from "@/lib/hooks/use-admin";
import { useImpersonationStore } from "@/lib/hooks/use-impersonation";
import { cn } from "@/lib/utils";

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
      <dd className="mt-1 text-sm text-foreground">{children}</dd>
    </div>
  );
}

// ─── Impersonation Dialog ─────────────────────────────────────────────────────

interface ImpersonationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenant: TenantSummary;
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
            <p className="text-sm text-destructive-600 dark:text-destructive-400">
              {errorMessage}
            </p>
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

// ─── Detail View ──────────────────────────────────────────────────────────────

function TenantDetail({ tenant }: { tenant: TenantSummary }) {
  const [dialogOpen, setDialogOpen] = useState(false);

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
      </div>

      {/* ── Info grid ── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Informacion de la clinica</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5">
            <InfoItem label="Slug">
              <code className="text-xs font-mono bg-[hsl(var(--muted))] px-1.5 py-0.5 rounded">
                {tenant.slug}
              </code>
            </InfoItem>
            <InfoItem label="Plan">
              <PlanBadge plan={tenant.plan_name} />
            </InfoItem>
            <InfoItem label="Estado">
              <StatusBadge status={tenant.status} />
            </InfoItem>
            <InfoItem label="Usuarios">
              {tenant.user_count}
            </InfoItem>
            <InfoItem label="Pacientes">
              {tenant.patient_count.toLocaleString("es-CO")}
            </InfoItem>
            <InfoItem label="Creado">
              {formatDate(tenant.created_at)}
            </InfoItem>
            <InfoItem label="ID">
              <code className="text-xs font-mono text-muted-foreground break-all">
                {tenant.id}
              </code>
            </InfoItem>
          </dl>
        </CardContent>
      </Card>

      {/* ── Actions card ── */}
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
              onClick={() => setDialogOpen(true)}
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

      {/* ── Dialog ── */}
      <ImpersonationDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        tenant={tenant}
      />
    </div>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function TenantDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-64 mb-3" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i}>
                <Skeleton className="h-3 w-16 mb-2" />
                <Skeleton className="h-4 w-32" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48 mb-2" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-9 w-40" />
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

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Tenant detail page — /admin/tenants/[id].
 *
 * Strategy: since there is no GET /admin/tenants/{id} endpoint, we fetch
 * page 1 with a large page_size (100) and find the matching tenant client-side.
 *
 * For production with thousands of tenants this approach should be replaced
 * with a dedicated detail endpoint. For MVP with < 100 tenants it is sufficient.
 */
export default function AdminTenantDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  // In Next.js 15+ params is a Promise — use `use()` to unwrap synchronously.
  const { id } = use(params);

  // Fetch a large page to find the tenant by ID client-side.
  const { data, isLoading, isError, refetch } = useAdminTenants({
    page: 1,
    page_size: 100,
  });

  const tenant = data?.items.find((t) => t.id === id) ?? null;

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
        <Card className="border-destructive-200 dark:border-destructive-700/40">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive-600 dark:text-destructive-400">
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
        <TenantDetail tenant={tenant} />
      )}

      {/* ── Not found ── */}
      {!isLoading && !isError && !tenant && (
        <TenantNotFound id={id} />
      )}
    </div>
  );
}
