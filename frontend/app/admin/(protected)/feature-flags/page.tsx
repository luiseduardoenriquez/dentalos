"use client";

import * as React from "react";
import {
  useAdminFeatureFlags,
  useCreateFeatureFlag,
  useUpdateFeatureFlag,
  useFlagChangeHistory,
  type FeatureFlagResponse,
  type FeatureFlagCreatePayload,
  type FeatureFlagUpdatePayload,
  type FlagChangeHistoryEntry,
} from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
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
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

// ─── Constants ─────────────────────────────────────────────────────────────────

const SCOPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "global", label: "Global" },
  { value: "tenant", label: "Por clínica" },
  { value: "plan", label: "Por plan" },
];

const SCOPE_LABELS: Record<string, string> = {
  global: "Global",
  tenant: "Por clínica",
  plan: "Por plan",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function truncate(text: string | null, max: number): string {
  if (!text) return "-";
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

function shortUUID(id: string | null): string {
  if (!id) return "-";
  return id.slice(0, 8) + "…";
}

function getScopeLabel(scope: string | null): string {
  if (!scope) return "Global";
  return SCOPE_LABELS[scope] ?? scope;
}

/**
 * Format an ISO date string to a localized display string (es-419).
 * Returns null if the input is null.
 */
function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  try {
    return new Intl.DateTimeFormat("es-419", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/**
 * Returns true if the given ISO date string is in the past.
 */
function isExpired(iso: string): boolean {
  return new Date(iso) < new Date();
}

// ─── Scope Badge ──────────────────────────────────────────────────────────────

function ScopeBadge({ scope }: { scope: string | null }) {
  if (!scope) {
    return (
      <Badge
        variant="outline"
        className="border-slate-300 bg-slate-100 text-slate-600 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400 text-xs"
      >
        Sin scope
      </Badge>
    );
  }

  if (scope === "global") {
    return (
      <Badge
        variant="outline"
        className="border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300 text-xs"
      >
        {getScopeLabel(scope)}
      </Badge>
    );
  }

  if (scope === "plan") {
    return (
      <Badge
        variant="outline"
        className="border-purple-300 bg-purple-50 text-purple-700 dark:border-purple-700 dark:bg-purple-950 dark:text-purple-300 text-xs"
      >
        {getScopeLabel(scope)}
      </Badge>
    );
  }

  if (scope === "tenant") {
    return (
      <Badge
        variant="outline"
        className="border-orange-300 bg-orange-50 text-orange-700 dark:border-orange-700 dark:bg-orange-950 dark:text-orange-300 text-xs"
      >
        {getScopeLabel(scope)}
      </Badge>
    );
  }

  // Fallback for unknown scopes
  return (
    <Badge variant="outline" className="text-xs">
      {getScopeLabel(scope)}
    </Badge>
  );
}

// ─── Expiry Badge ─────────────────────────────────────────────────────────────

function ExpiryBadge({ expiresAt }: { expiresAt: string | null }) {
  if (!expiresAt) return null;

  const expired = isExpired(expiresAt);

  if (expired) {
    return (
      <Badge
        variant="outline"
        className="border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300 text-xs"
      >
        Expirado
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className="border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300 text-xs"
    >
      Expira: {formatDate(expiresAt)}
    </Badge>
  );
}

// ─── Flag Change History Modal ─────────────────────────────────────────────────

interface FlagHistoryModalProps {
  flag: FeatureFlagResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function FlagHistoryModal({ flag, open, onOpenChange }: FlagHistoryModalProps) {
  const { data: history, isLoading, isError } = useFlagChangeHistory(
    open ? flag.id : "",
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Historial de cambios</DialogTitle>
          <DialogDescription>
            Cambios registrados para el flag{" "}
            <code className="rounded bg-[hsl(var(--muted))] px-1.5 py-0.5 font-mono text-xs">
              {flag.flag_name}
            </code>
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-[120px]">
          {isLoading && (
            <div className="flex flex-col gap-3 py-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <Skeleton className="h-4 w-28" />
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-4" />
                  <Skeleton className="h-4 w-16" />
                </div>
              ))}
            </div>
          )}

          {isError && !isLoading && (
            <p className="py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
              Error al cargar el historial. Intenta de nuevo.
            </p>
          )}

          {!isLoading && !isError && history && history.length === 0 && (
            <p className="py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No hay cambios registrados para este flag.
            </p>
          )}

          {!isLoading && !isError && history && history.length > 0 && (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="whitespace-nowrap">Fecha</TableHead>
                    <TableHead>Campo</TableHead>
                    <TableHead>Valor anterior</TableHead>
                    <TableHead className="text-center">→</TableHead>
                    <TableHead>Valor nuevo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((entry: FlagChangeHistoryEntry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="whitespace-nowrap text-xs text-[hsl(var(--muted-foreground))]">
                        {formatDate(entry.created_at) ?? entry.created_at}
                      </TableCell>
                      <TableCell>
                        <code className="rounded bg-[hsl(var(--muted))] px-1 py-0.5 font-mono text-xs">
                          {entry.field_changed}
                        </code>
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {entry.old_value ?? (
                          <span className="italic opacity-60">vacío</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center text-[hsl(var(--muted-foreground))]">
                        →
                      </TableCell>
                      <TableCell className="text-sm font-medium">
                        {entry.new_value ?? (
                          <span className="italic opacity-60">vacío</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function FlagsLoadingSkeleton() {
  return (
    <Card>
      <CardContent className="p-0">
        <div className="divide-y divide-[hsl(var(--border))]">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center gap-4 px-6 py-4">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-4 w-24 ml-auto" />
              <Skeleton className="h-8 w-16" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Flag Form Fields ──────────────────────────────────────────────────────────
// Shared between create and edit dialogs.

interface FlagFormState {
  flag_name: string;
  description: string;
  scope: string;
  enabled: boolean;
  tenant_id: string;
  expires_at: string; // ISO date string (YYYY-MM-DD) or empty string
  reason: string;
}

interface FlagFormFieldsProps {
  state: FlagFormState;
  onChange: (updates: Partial<FlagFormState>) => void;
  nameReadOnly?: boolean;
}

function FlagFormFields({ state, onChange, nameReadOnly = false }: FlagFormFieldsProps) {
  return (
    <div className="grid gap-4 py-2">
      {/* Flag name */}
      <div className="space-y-1.5">
        <Label htmlFor="flag-key">
          Nombre del flag{" "}
          <span className="text-[hsl(var(--muted-foreground))]">(snake_case)</span>
        </Label>
        <Input
          id="flag-key"
          type="text"
          value={state.flag_name}
          onChange={(e) => onChange({ flag_name: e.target.value })}
          readOnly={nameReadOnly}
          placeholder="ej: voice_transcription_enabled"
          className={cn(
            "font-mono text-sm",
            nameReadOnly && "cursor-not-allowed opacity-60 bg-[hsl(var(--muted))]",
          )}
          aria-describedby="flag-key-hint"
        />
        {!nameReadOnly && (
          <p id="flag-key-hint" className="text-xs text-[hsl(var(--muted-foreground))]">
            El nombre es permanente una vez creado.
          </p>
        )}
      </div>

      {/* Scope */}
      <div className="space-y-1.5">
        <Label htmlFor="flag-scope">Alcance</Label>
        <select
          id="flag-scope"
          value={state.scope}
          onChange={(e) => onChange({ scope: e.target.value })}
          className={cn(
            "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
            "px-3 py-2 text-sm text-foreground shadow-sm",
            "focus:outline-none focus:ring-2 focus:ring-primary-600",
          )}
        >
          {SCOPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <Label htmlFor="flag-description">Descripcion (opcional)</Label>
        <textarea
          id="flag-description"
          rows={3}
          value={state.description}
          onChange={(e) => onChange({ description: e.target.value })}
          placeholder="Describe para qué sirve este flag..."
          className={cn(
            "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
            "px-3 py-2 text-sm text-foreground shadow-sm resize-y",
            "focus:outline-none focus:ring-2 focus:ring-primary-600",
          )}
        />
      </div>

      {/* Tenant ID (shown only when scope = "tenant") */}
      {state.scope === "tenant" && (
        <div className="space-y-1.5">
          <Label htmlFor="flag-tenant-id">
            UUID de clínica{" "}
            <span className="text-[hsl(var(--muted-foreground))]">(opcional)</span>
          </Label>
          <Input
            id="flag-tenant-id"
            type="text"
            value={state.tenant_id}
            onChange={(e) => onChange({ tenant_id: e.target.value })}
            placeholder="ej: abc123de-f456-..."
            className="font-mono text-sm"
          />
        </div>
      )}

      {/* Expiry date */}
      <div className="space-y-1.5">
        <Label htmlFor="flag-expires-at">
          Fecha de expiracion{" "}
          <span className="text-[hsl(var(--muted-foreground))]">(opcional)</span>
        </Label>
        <Input
          id="flag-expires-at"
          type="date"
          value={state.expires_at}
          onChange={(e) => onChange({ expires_at: e.target.value })}
          className="text-sm"
        />
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          El flag se desactivara automaticamente despues de esta fecha.
        </p>
      </div>

      {/* Reason */}
      <div className="space-y-1.5">
        <Label htmlFor="flag-reason">
          Razon del cambio{" "}
          <span className="text-[hsl(var(--muted-foreground))]">(opcional)</span>
        </Label>
        <textarea
          id="flag-reason"
          rows={2}
          value={state.reason}
          onChange={(e) => onChange({ reason: e.target.value })}
          placeholder="ej: Activado para prueba A/B en clinicas piloto..."
          className={cn(
            "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--background))]",
            "px-3 py-2 text-sm text-foreground shadow-sm resize-y",
            "focus:outline-none focus:ring-2 focus:ring-primary-600",
          )}
        />
      </div>

      {/* Enabled toggle */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="flag-enabled"
          checked={state.enabled}
          onCheckedChange={(checked) => onChange({ enabled: checked === true })}
        />
        <Label htmlFor="flag-enabled" className="cursor-pointer">
          Flag activo
        </Label>
      </div>
    </div>
  );
}

// ─── Create Flag Dialog ────────────────────────────────────────────────────────

interface CreateFlagDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const EMPTY_CREATE_STATE: FlagFormState = {
  flag_name: "",
  description: "",
  scope: "global",
  enabled: false,
  tenant_id: "",
  expires_at: "",
  reason: "",
};

function CreateFlagDialog({ open, onOpenChange }: CreateFlagDialogProps) {
  const { success, error } = useToast();
  const createFlag = useCreateFeatureFlag();
  const [form, setForm] = React.useState<FlagFormState>(EMPTY_CREATE_STATE);

  // Reset form when dialog opens
  React.useEffect(() => {
    if (open) setForm(EMPTY_CREATE_STATE);
  }, [open]);

  function handleCreate() {
    if (!form.flag_name.trim()) return;

    const payload: FeatureFlagCreatePayload = {
      flag_name: form.flag_name.trim(),
      description: form.description.trim() || undefined,
      scope: form.scope || undefined,
      enabled: form.enabled,
      tenant_id: form.tenant_id.trim() || undefined,
      expires_at: form.expires_at.trim() || undefined,
      reason: form.reason.trim() || undefined,
    };

    createFlag.mutate(payload, {
      onSuccess: () => {
        success("Flag creado", `"${payload.flag_name}" se creó correctamente.`);
        onOpenChange(false);
      },
      onError: () => {
        error("Error al crear", "No se pudo crear el flag. Intenta de nuevo.");
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Crear feature flag</DialogTitle>
          <DialogDescription>
            Los flags permiten activar funcionalidades por alcance global, por
            clínica o por plan de suscripcion.
          </DialogDescription>
        </DialogHeader>

        <FlagFormFields
          state={form}
          onChange={(updates) => setForm((prev) => ({ ...prev, ...updates }))}
          nameReadOnly={false}
        />

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={createFlag.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleCreate}
            disabled={createFlag.isPending || !form.flag_name.trim()}
          >
            {createFlag.isPending ? "Creando..." : "Crear"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Flag Dialog ──────────────────────────────────────────────────────────

interface EditFlagDialogProps {
  flag: FeatureFlagResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function EditFlagDialog({ flag, open, onOpenChange }: EditFlagDialogProps) {
  const { success, error } = useToast();
  const updateFlag = useUpdateFeatureFlag();

  // Convert ISO datetime to YYYY-MM-DD for the date input
  function toDateInputValue(iso: string | null): string {
    if (!iso) return "";
    try {
      return iso.slice(0, 10); // "2026-06-15T00:00:00Z" → "2026-06-15"
    } catch {
      return "";
    }
  }

  const [form, setForm] = React.useState<FlagFormState>({
    flag_name: flag.flag_name,
    description: flag.description ?? "",
    scope: flag.scope ?? "global",
    enabled: flag.enabled,
    tenant_id: flag.tenant_id ?? "",
    expires_at: toDateInputValue(flag.expires_at),
    reason: flag.reason ?? "",
  });

  // Sync form when the dialog re-opens with a (possibly different) flag
  React.useEffect(() => {
    if (open) {
      setForm({
        flag_name: flag.flag_name,
        description: flag.description ?? "",
        scope: flag.scope ?? "global",
        enabled: flag.enabled,
        tenant_id: flag.tenant_id ?? "",
        expires_at: toDateInputValue(flag.expires_at),
        reason: flag.reason ?? "",
      });
    }
  }, [open, flag]);

  function handleSave() {
    const payload: FeatureFlagUpdatePayload = {
      description: form.description.trim() || undefined,
      enabled: form.enabled,
      scope: form.scope || undefined,
      tenant_id: form.tenant_id.trim() || undefined,
      expires_at: form.expires_at.trim() || undefined,
      reason: form.reason.trim() || undefined,
    };

    updateFlag.mutate(
      { id: flag.id, payload },
      {
        onSuccess: () => {
          success("Flag actualizado", "Los cambios se guardaron correctamente.");
          onOpenChange(false);
        },
        onError: () => {
          error("Error al guardar", "No se pudo actualizar el flag. Intenta de nuevo.");
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Editar feature flag</DialogTitle>
          <DialogDescription>
            El nombre del flag no puede modificarse una vez creado.
          </DialogDescription>
        </DialogHeader>

        <FlagFormFields
          state={form}
          onChange={(updates) => setForm((prev) => ({ ...prev, ...updates }))}
          nameReadOnly={true}
        />

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={updateFlag.isPending}
          >
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={updateFlag.isPending}>
            {updateFlag.isPending ? "Guardando..." : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminFeatureFlagsPage() {
  const { data: flags, isLoading, isError, refetch } = useAdminFeatureFlags();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editingFlag, setEditingFlag] = React.useState<FeatureFlagResponse | null>(null);
  const [historyFlag, setHistoryFlag] = React.useState<FeatureFlagResponse | null>(null);

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Feature Flags</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Controla qué funcionalidades están activas a nivel global, por
            clínica o por plan.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>Crear flag</Button>
      </div>

      {/* Loading state */}
      {isLoading && <FlagsLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar los feature flags. Verifica la conexion con la API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Flags table */}
      {!isLoading && !isError && flags && (
        <>
          {flags.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-[hsl(var(--muted-foreground))]">
                No hay feature flags configurados. Crea el primero.
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader className="pb-0">
                <CardTitle className="text-base">
                  {flags.length} {flags.length === 1 ? "flag" : "flags"} en total
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0 mt-4">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="min-w-[200px]">Nombre</TableHead>
                        <TableHead>Alcance</TableHead>
                        <TableHead>Clínica / Plan</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Expiracion</TableHead>
                        <TableHead className="max-w-[180px]">Descripcion</TableHead>
                        <TableHead className="max-w-[180px]">Razon</TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {flags.map((flag) => (
                        <TableRow key={flag.id}>
                          {/* Flag name */}
                          <TableCell>
                            <code className="rounded bg-[hsl(var(--muted))] px-1.5 py-0.5 font-mono text-xs">
                              {flag.flag_name}
                            </code>
                          </TableCell>

                          {/* Scope badge — colored by scope type */}
                          <TableCell>
                            <ScopeBadge scope={flag.scope} />
                          </TableCell>

                          {/* Tenant ID or plan_filter */}
                          <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                            {flag.scope === "tenant" && flag.tenant_id ? (
                              <span title={flag.tenant_id}>
                                {shortUUID(flag.tenant_id)}
                              </span>
                            ) : flag.scope === "plan" && flag.plan_filter ? (
                              <span>{flag.plan_filter}</span>
                            ) : (
                              "—"
                            )}
                          </TableCell>

                          {/* Enabled status */}
                          <TableCell>
                            <Badge
                              variant={flag.enabled ? "success" : "secondary"}
                            >
                              {flag.enabled ? "Activo" : "Inactivo"}
                            </Badge>
                          </TableCell>

                          {/* Expiry indicator */}
                          <TableCell>
                            <ExpiryBadge expiresAt={flag.expires_at} />
                            {!flag.expires_at && (
                              <span className="text-sm text-[hsl(var(--muted-foreground))]">
                                —
                              </span>
                            )}
                          </TableCell>

                          {/* Description (truncated, tooltip on hover) */}
                          <TableCell
                            className="max-w-[180px] text-sm text-[hsl(var(--muted-foreground))]"
                            title={flag.description ?? undefined}
                          >
                            {truncate(flag.description, 60)}
                          </TableCell>

                          {/* Reason (truncated to 50 chars, tooltip on hover) */}
                          <TableCell
                            className="max-w-[180px] text-sm text-[hsl(var(--muted-foreground))]"
                            title={flag.reason ?? undefined}
                          >
                            {truncate(flag.reason, 50)}
                          </TableCell>

                          {/* Actions */}
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setHistoryFlag(flag)}
                              >
                                Historial
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setEditingFlag(flag)}
                              >
                                Editar
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Create dialog */}
      <CreateFlagDialog open={createOpen} onOpenChange={setCreateOpen} />

      {/* Edit dialog */}
      {editingFlag && (
        <EditFlagDialog
          flag={editingFlag}
          open={editingFlag !== null}
          onOpenChange={(open) => {
            if (!open) setEditingFlag(null);
          }}
        />
      )}

      {/* Change history modal — lazy: only mounts when historyFlag is set */}
      {historyFlag && (
        <FlagHistoryModal
          flag={historyFlag}
          open={historyFlag !== null}
          onOpenChange={(open) => {
            if (!open) setHistoryFlag(null);
          }}
        />
      )}
    </div>
  );
}
