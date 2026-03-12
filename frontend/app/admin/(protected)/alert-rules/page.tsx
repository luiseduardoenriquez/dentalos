"use client";

import { useState, useEffect } from "react";
import {
  useAlertRules,
  useCreateAlertRule,
  useUpdateAlertRule,
  useDeleteAlertRule,
  type AlertRuleResponse,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import {
  Bell,
  Plus,
  Pencil,
  Trash2,
  AlertCircle,
  TrendingDown,
  Clock,
  Activity,
  TrendingUp,
  DollarSign,
  Mail,
  BellRing,
} from "lucide-react";

// ─── Constants ─────────────────────────────────────────────────────────────────

const CONDITION_OPTIONS = [
  { value: "churn_rate_high", label: "Tasa de churn alta" },
  { value: "queue_depth_high", label: "Cola saturada" },
  { value: "trial_expiring", label: "Trial por vencer" },
  { value: "health_degraded", label: "Salud degradada" },
  { value: "signup_spike", label: "Pico de registros" },
  { value: "revenue_drop", label: "Caída de ingresos" },
] as const;

const CHANNEL_OPTIONS = [
  { value: "in_app", label: "Notificación" },
  { value: "email", label: "Email" },
  { value: "both", label: "Ambos" },
] as const;

const CONDITION_LABELS: Record<string, string> = {
  churn_rate_high: "Tasa de churn alta",
  queue_depth_high: "Cola saturada",
  trial_expiring: "Trial por vencer",
  health_degraded: "Salud degradada",
  signup_spike: "Pico de registros",
  revenue_drop: "Caída de ingresos",
};

const CHANNEL_LABELS: Record<string, string> = {
  in_app: "Notificación",
  email: "Email",
  both: "Ambos",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("es-419", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

// ─── Condition Badge ───────────────────────────────────────────────────────────

function ConditionBadge({ condition }: { condition: string }) {
  const label = CONDITION_LABELS[condition] ?? condition;

  if (condition === "churn_rate_high") {
    return (
      <Badge
        variant="outline"
        className="border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300 text-xs gap-1"
      >
        <TrendingDown className="h-3 w-3" />
        {label}
      </Badge>
    );
  }

  if (condition === "queue_depth_high") {
    return (
      <Badge
        variant="outline"
        className="border-orange-300 bg-orange-50 text-orange-700 dark:border-orange-700 dark:bg-orange-950 dark:text-orange-300 text-xs gap-1"
      >
        <Activity className="h-3 w-3" />
        {label}
      </Badge>
    );
  }

  if (condition === "trial_expiring") {
    return (
      <Badge
        variant="warning"
        className="text-xs gap-1"
      >
        <Clock className="h-3 w-3" />
        {label}
      </Badge>
    );
  }

  if (condition === "health_degraded") {
    return (
      <Badge
        variant="destructive"
        className="text-xs gap-1"
      >
        <AlertCircle className="h-3 w-3" />
        {label}
      </Badge>
    );
  }

  if (condition === "signup_spike") {
    return (
      <Badge
        variant="outline"
        className="border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300 text-xs gap-1"
      >
        <TrendingUp className="h-3 w-3" />
        {label}
      </Badge>
    );
  }

  if (condition === "revenue_drop") {
    return (
      <Badge
        variant="outline"
        className="border-purple-300 bg-purple-50 text-purple-700 dark:border-purple-700 dark:bg-purple-950 dark:text-purple-300 text-xs gap-1"
      >
        <DollarSign className="h-3 w-3" />
        {label}
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className="text-xs">
      {label}
    </Badge>
  );
}

// ─── Channel Badge ─────────────────────────────────────────────────────────────

function ChannelBadge({ channel }: { channel: string }) {
  const label = CHANNEL_LABELS[channel] ?? channel;

  if (channel === "email") {
    return (
      <Badge
        variant="outline"
        className="border-sky-300 bg-sky-50 text-sky-700 dark:border-sky-700 dark:bg-sky-950 dark:text-sky-300 text-xs gap-1"
      >
        <Mail className="h-3 w-3" />
        {label}
      </Badge>
    );
  }

  if (channel === "both") {
    return (
      <Badge
        variant="outline"
        className="border-teal-300 bg-teal-50 text-teal-700 dark:border-teal-700 dark:bg-teal-950 dark:text-teal-300 text-xs gap-1"
      >
        <BellRing className="h-3 w-3" />
        {label}
      </Badge>
    );
  }

  // in_app
  return (
    <Badge
      variant="outline"
      className="border-indigo-300 bg-indigo-50 text-indigo-700 dark:border-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 text-xs gap-1"
    >
      <Bell className="h-3 w-3" />
      {label}
    </Badge>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function AlertRulesLoadingSkeleton() {
  return (
    <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
      <CardContent className="p-0">
        <div className="divide-y divide-[hsl(var(--border))]">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-4 px-6 py-4">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-5 w-28" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-4 w-32 ml-auto" />
              <Skeleton className="h-8 w-8" />
              <Skeleton className="h-8 w-8" />
              <Skeleton className="h-8 w-8" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Toggle Active Inline Button ───────────────────────────────────────────────

interface ToggleActiveButtonProps {
  rule: AlertRuleResponse;
}

function ToggleActiveButton({ rule }: ToggleActiveButtonProps) {
  const { success, error } = useToast();
  const updateRule = useUpdateAlertRule();

  function handleToggle() {
    updateRule.mutate(
      { id: rule.id, is_active: !rule.is_active },
      {
        onSuccess: () => {
          success(
            rule.is_active ? "Regla desactivada" : "Regla activada",
            rule.is_active
              ? "La regla ya no monitoreará esta condición."
              : "La regla está monitoreando activamente.",
          );
        },
        onError: () => {
          error(
            "Error al actualizar",
            "No se pudo cambiar el estado de la regla.",
          );
        },
      },
    );
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleToggle}
      disabled={updateRule.isPending}
      className={cn(
        "text-xs h-7 px-2",
        rule.is_active
          ? "text-[hsl(var(--muted-foreground))] hover:text-foreground"
          : "text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300",
      )}
    >
      {rule.is_active ? "Desactivar" : "Activar"}
    </Button>
  );
}

// ─── Alert Rule Form State ─────────────────────────────────────────────────────

interface AlertRuleFormState {
  name: string;
  condition: string;
  threshold: string;
  channel: string;
  is_active: boolean;
}

const EMPTY_FORM: AlertRuleFormState = {
  name: "",
  condition: "churn_rate_high",
  threshold: "",
  channel: "in_app",
  is_active: true,
};

// ─── Alert Rule Form Fields ────────────────────────────────────────────────────
// Shared between create and edit dialogs.

interface AlertRuleFormFieldsProps {
  state: AlertRuleFormState;
  onChange: (updates: Partial<AlertRuleFormState>) => void;
}

function AlertRuleFormFields({ state, onChange }: AlertRuleFormFieldsProps) {
  return (
    <div className="grid gap-4 py-2">
      {/* Nombre */}
      <div className="space-y-1.5">
        <Label htmlFor="rule-name">
          Nombre <span className="text-red-500">*</span>
        </Label>
        <Input
          id="rule-name"
          type="text"
          value={state.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="ej: Alerta churn mensual"
          className="text-sm"
        />
      </div>

      {/* Condición */}
      <div className="space-y-1.5">
        <Label htmlFor="rule-condition">Condición</Label>
        <Select
          value={state.condition}
          onValueChange={(val) => onChange({ condition: val })}
        >
          <SelectTrigger id="rule-condition" className="text-sm">
            <SelectValue placeholder="Selecciona una condición" />
          </SelectTrigger>
          <SelectContent>
            {CONDITION_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Umbral */}
      <div className="space-y-1.5">
        <Label htmlFor="rule-threshold">
          Umbral <span className="text-red-500">*</span>
        </Label>
        <Input
          id="rule-threshold"
          type="text"
          value={state.threshold}
          onChange={(e) => onChange({ threshold: e.target.value })}
          placeholder="ej: 5%, 100, 3 días"
          className="text-sm"
        />
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          Define el valor límite que dispara la alerta (ej: 5%, 100 mensajes,
          3 días).
        </p>
      </div>

      {/* Canal */}
      <div className="space-y-1.5">
        <Label htmlFor="rule-channel">Canal de notificación</Label>
        <Select
          value={state.channel}
          onValueChange={(val) => onChange({ channel: val })}
        >
          <SelectTrigger id="rule-channel" className="text-sm">
            <SelectValue placeholder="Selecciona un canal" />
          </SelectTrigger>
          <SelectContent>
            {CHANNEL_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Activa */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="rule-active"
          checked={state.is_active}
          onCheckedChange={(checked) =>
            onChange({ is_active: checked === true })
          }
        />
        <Label htmlFor="rule-active" className="cursor-pointer">
          Regla activa
        </Label>
        <span className="text-xs text-[hsl(var(--muted-foreground))]">
          — la regla monitoreará la condición en tiempo real
        </span>
      </div>
    </div>
  );
}

// ─── Create Alert Rule Dialog ──────────────────────────────────────────────────

interface CreateAlertRuleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function CreateAlertRuleDialog({
  open,
  onOpenChange,
}: CreateAlertRuleDialogProps) {
  const { success, error } = useToast();
  const createRule = useCreateAlertRule();
  const [form, setForm] = useState<AlertRuleFormState>(EMPTY_FORM);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) setForm(EMPTY_FORM);
  }, [open]);

  const isValid =
    form.name.trim() !== "" && form.threshold.trim() !== "";

  function handleCreate() {
    if (!isValid) return;

    createRule.mutate(
      {
        name: form.name.trim(),
        condition: form.condition,
        threshold: form.threshold.trim(),
        channel: form.channel,
        is_active: form.is_active,
      },
      {
        onSuccess: () => {
          success(
            "Regla creada",
            `"${form.name.trim()}" se configuró correctamente.`,
          );
          onOpenChange(false);
          setForm(EMPTY_FORM);
        },
        onError: () => {
          error(
            "Error al crear",
            "No se pudo crear la regla de alerta. Intenta de nuevo.",
          );
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nueva regla de alerta</DialogTitle>
          <DialogDescription>
            Las reglas monitorean condiciones de la plataforma y notifican
            automáticamente cuando se supera el umbral configurado.
          </DialogDescription>
        </DialogHeader>

        <AlertRuleFormFields
          state={form}
          onChange={(updates) => setForm((prev) => ({ ...prev, ...updates }))}
        />

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={createRule.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleCreate}
            disabled={createRule.isPending || !isValid}
          >
            {createRule.isPending ? "Creando..." : "Crear Regla"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Alert Rule Dialog ────────────────────────────────────────────────────

interface EditAlertRuleDialogProps {
  rule: AlertRuleResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function EditAlertRuleDialog({
  rule,
  open,
  onOpenChange,
}: EditAlertRuleDialogProps) {
  const { success, error } = useToast();
  const updateRule = useUpdateAlertRule();

  const [form, setForm] = useState<AlertRuleFormState>({
    name: rule.name,
    condition: rule.condition,
    threshold: rule.threshold,
    channel: rule.channel,
    is_active: rule.is_active,
  });

  // Sync form when dialog opens with a (potentially different) rule
  useEffect(() => {
    if (open) {
      setForm({
        name: rule.name,
        condition: rule.condition,
        threshold: rule.threshold,
        channel: rule.channel,
        is_active: rule.is_active,
      });
    }
  }, [open, rule]);

  const isValid =
    form.name.trim() !== "" && form.threshold.trim() !== "";

  function handleSave() {
    if (!isValid) return;

    updateRule.mutate(
      {
        id: rule.id,
        name: form.name.trim(),
        condition: form.condition,
        threshold: form.threshold.trim(),
        channel: form.channel,
        is_active: form.is_active,
      },
      {
        onSuccess: () => {
          success("Regla actualizada", "Los cambios se guardaron correctamente.");
          onOpenChange(false);
        },
        onError: () => {
          error(
            "Error al guardar",
            "No se pudo actualizar la regla. Intenta de nuevo.",
          );
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar regla de alerta</DialogTitle>
          <DialogDescription>
            Modifica los parámetros de monitoreo de esta regla. Los cambios
            aplican de inmediato.
          </DialogDescription>
        </DialogHeader>

        <AlertRuleFormFields
          state={form}
          onChange={(updates) => setForm((prev) => ({ ...prev, ...updates }))}
        />

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={updateRule.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
            disabled={updateRule.isPending || !isValid}
          >
            {updateRule.isPending ? "Guardando..." : "Guardar cambios"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Delete Confirm Dialog ─────────────────────────────────────────────────────

interface DeleteConfirmDialogProps {
  rule: AlertRuleResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function DeleteConfirmDialog({
  rule,
  open,
  onOpenChange,
}: DeleteConfirmDialogProps) {
  const { success, error } = useToast();
  const deleteRule = useDeleteAlertRule();

  function handleDelete() {
    deleteRule.mutate(rule.id, {
      onSuccess: () => {
        success(
          "Regla eliminada",
          `"${rule.name}" se eliminó correctamente.`,
        );
        onOpenChange(false);
      },
      onError: () => {
        error(
          "Error al eliminar",
          "No se pudo eliminar la regla. Intenta de nuevo.",
        );
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Eliminar regla de alerta</DialogTitle>
          <DialogDescription>
            Esta acción eliminará permanentemente la regla{" "}
            <strong>"{rule.name}"</strong>. El sistema dejará de monitorear
            esta condición. ¿Deseas continuar?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={deleteRule.isPending}
          >
            Cancelar
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteRule.isPending}
          >
            {deleteRule.isPending ? "Eliminando..." : "Eliminar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminAlertRulesPage() {
  const { data, isLoading, isError, refetch } = useAlertRules();
  const [createOpen, setCreateOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRuleResponse | null>(
    null,
  );
  const [deletingRule, setDeletingRule] = useState<AlertRuleResponse | null>(
    null,
  );

  const rules = data?.items ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <h1 className="text-2xl font-bold tracking-tight">
              Alertas Automáticas
            </h1>
          </div>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Configurar reglas de alertas para monitoreo automático
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Nueva Regla
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && <AlertRulesLoadingSkeleton />}

      {/* Error state */}
      {isError && !isLoading && (
        <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <AlertCircle className="h-8 w-8 text-[hsl(var(--muted-foreground))]" />
            <p className="text-[hsl(var(--muted-foreground))]">
              Error al cargar las reglas de alerta. Verifica la conexión con la
              API.
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Rules table */}
      {!isLoading && !isError && (
        <>
          {rules.length === 0 ? (
            <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
              <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
                <Bell className="h-10 w-10 text-[hsl(var(--muted-foreground))] opacity-40" />
                <p className="text-[hsl(var(--muted-foreground))]">
                  No hay reglas configuradas
                </p>
                <p className="text-sm text-[hsl(var(--muted-foreground))] max-w-xs">
                  Crea la primera regla para comenzar a monitorear condiciones
                  críticas de la plataforma.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCreateOpen(true)}
                  className="gap-1 mt-1"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Nueva Regla
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
              <CardHeader className="pb-0">
                <CardTitle className="text-base">
                  {data?.total ?? rules.length}{" "}
                  {(data?.total ?? rules.length) === 1
                    ? "regla configurada"
                    : "reglas configuradas"}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0 mt-4">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="min-w-[180px]">Nombre</TableHead>
                        <TableHead className="min-w-[160px]">
                          Condición
                        </TableHead>
                        <TableHead>Umbral</TableHead>
                        <TableHead>Canal</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead className="whitespace-nowrap">
                          Último disparo
                        </TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rules.map((rule) => (
                        <TableRow key={rule.id}>
                          {/* Nombre */}
                          <TableCell>
                            <p className="text-sm font-medium">{rule.name}</p>
                          </TableCell>

                          {/* Condición */}
                          <TableCell>
                            <ConditionBadge condition={rule.condition} />
                          </TableCell>

                          {/* Umbral */}
                          <TableCell>
                            <code className="rounded bg-[hsl(var(--muted))] px-1.5 py-0.5 font-mono text-xs">
                              {rule.threshold}
                            </code>
                          </TableCell>

                          {/* Canal */}
                          <TableCell>
                            <ChannelBadge channel={rule.channel} />
                          </TableCell>

                          {/* Estado */}
                          <TableCell>
                            <Badge
                              variant={rule.is_active ? "success" : "secondary"}
                            >
                              {rule.is_active ? "Activa" : "Inactiva"}
                            </Badge>
                          </TableCell>

                          {/* Último disparo */}
                          <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                            {formatDate(rule.last_triggered_at)}
                          </TableCell>

                          {/* Acciones */}
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <ToggleActiveButton rule={rule} />
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-[hsl(var(--muted-foreground))] hover:text-foreground"
                                title="Editar regla"
                                onClick={() => setEditingRule(rule)}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                                <span className="sr-only">Editar</span>
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-[hsl(var(--muted-foreground))] hover:text-red-600 dark:hover:text-red-400"
                                title="Eliminar regla"
                                onClick={() => setDeletingRule(rule)}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                                <span className="sr-only">Eliminar</span>
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
      <CreateAlertRuleDialog open={createOpen} onOpenChange={setCreateOpen} />

      {/* Edit dialog — only mounted when a rule is selected */}
      {editingRule && (
        <EditAlertRuleDialog
          rule={editingRule}
          open={editingRule !== null}
          onOpenChange={(open) => {
            if (!open) setEditingRule(null);
          }}
        />
      )}

      {/* Delete confirm dialog — only mounted when a rule is selected */}
      {deletingRule && (
        <DeleteConfirmDialog
          rule={deletingRule}
          open={deletingRule !== null}
          onOpenChange={(open) => {
            if (!open) setDeletingRule(null);
          }}
        />
      )}
    </div>
  );
}
