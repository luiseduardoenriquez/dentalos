"use client";

import * as React from "react";
import {
  useAdminFeatureFlags,
  useCreateFeatureFlag,
  useUpdateFeatureFlag,
  type FeatureFlagResponse,
  type FeatureFlagCreatePayload,
  type FeatureFlagUpdatePayload,
} from "@/lib/hooks/use-admin";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
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
  // Show first 8 chars of UUID for readability
  return id.slice(0, 8) + "…";
}

function getScopeLabel(scope: string | null): string {
  if (!scope) return "Global";
  return SCOPE_LABELS[scope] ?? scope;
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
  tenant_id: string; // single tenant UUID or empty string
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

  const [form, setForm] = React.useState<FlagFormState>({
    flag_name: flag.flag_name,
    description: flag.description ?? "",
    scope: flag.scope ?? "global",
    enabled: flag.enabled,
    tenant_id: flag.tenant_id ?? "",
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
      });
    }
  }, [open, flag]);

  function handleSave() {
    const payload: FeatureFlagUpdatePayload = {
      description: form.description.trim() || undefined,
      enabled: form.enabled,
      scope: form.scope || undefined,
      tenant_id: form.tenant_id.trim() || undefined,
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
  const [editingFlag, setEditingFlag] = React.useState<FeatureFlagResponse | null>(
    null,
  );

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
                        <TableHead className="max-w-[220px]">
                          Descripcion
                        </TableHead>
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

                          {/* Scope badge */}
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {getScopeLabel(flag.scope)}
                            </Badge>
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

                          {/* Description (truncated) */}
                          <TableCell
                            className="max-w-[220px] text-sm text-[hsl(var(--muted-foreground))]"
                            title={flag.description ?? undefined}
                          >
                            {truncate(flag.description, 60)}
                          </TableCell>

                          {/* Actions */}
                          <TableCell className="text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setEditingFlag(flag)}
                            >
                              Editar
                            </Button>
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
    </div>
  );
}
