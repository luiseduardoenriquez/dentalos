"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { apiGet, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type ReminderChannel = "sms" | "email" | "whatsapp";

interface ReminderRule {
  hours_before: number;
  channel: ReminderChannel;
  message_template: string;
}

interface RemindersConfig {
  rules: ReminderRule[];
  default_channels: ReminderChannel[];
  /** Maximum number of reminder rules allowed by the current plan */
  max_reminders_allowed: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const REMINDER_QUERY_KEY = ["settings", "reminders"] as const;

const CHANNEL_OPTIONS: { value: ReminderChannel; label: string }[] = [
  { value: "sms", label: "SMS" },
  { value: "email", label: "Correo electrónico" },
  { value: "whatsapp", label: "WhatsApp" },
];

const CHANNEL_LABELS: Record<ReminderChannel, string> = {
  sms: "SMS",
  email: "Correo electrónico",
  whatsapp: "WhatsApp",
};

const DEFAULT_RULE: ReminderRule = {
  hours_before: 24,
  channel: "whatsapp",
  message_template:
    "Hola {{nombre}}, te recordamos tu cita en {{clinica}} el {{fecha}} a las {{hora}}. Para cancelar responde CANCELAR.",
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

function useRemindersConfig() {
  return useQuery({
    queryKey: REMINDER_QUERY_KEY,
    queryFn: () => apiGet<RemindersConfig>("/settings/reminders"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

function useUpdateRemindersConfig() {
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (data: RemindersConfig) => apiPut<RemindersConfig>("/settings/reminders", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REMINDER_QUERY_KEY });
      success("Recordatorios guardados", "La configuración de recordatorios fue actualizada.");
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo guardar la configuración. Inténtalo de nuevo.";
      error("Error al guardar recordatorios", message);
    },
  });
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function RemindersSkeleton() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div className="space-y-1">
        <Skeleton className="h-7 w-52" />
        <Skeleton className="h-4 w-72" />
      </div>
      {[1, 2].map((i) => (
        <div key={i} className="border rounded-xl p-6 space-y-4">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-64" />
          <div className="grid grid-cols-2 gap-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
          <Skeleton className="h-20 w-full" />
        </div>
      ))}
    </div>
  );
}

// ─── Reminder Rule Card ───────────────────────────────────────────────────────

interface ReminderRuleCardProps {
  rule: ReminderRule;
  index: number;
  onUpdate: (index: number, field: keyof ReminderRule, value: unknown) => void;
  onRemove: (index: number) => void;
  canRemove: boolean;
}

function ReminderRuleCard({ rule, index, onUpdate, onRemove, canRemove }: ReminderRuleCardProps) {
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] p-4 space-y-4">
      {/* ── Rule header ───────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">
          Recordatorio {index + 1}
        </p>
        {canRemove && (
          <button
            type="button"
            onClick={() => onRemove(index)}
            aria-label={`Eliminar recordatorio ${index + 1}`}
            className="flex h-8 w-8 items-center justify-center rounded-md text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] hover:text-destructive-600 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* ── Hours before + channel ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <Label htmlFor={`hours_before_${index}`}>
            Horas de anticipación <span className="text-destructive-600">*</span>
          </Label>
          <Input
            id={`hours_before_${index}`}
            type="number"
            min={1}
            max={168}
            value={rule.hours_before}
            onChange={(e) => onUpdate(index, "hours_before", Number(e.target.value))}
            aria-label="Horas antes de la cita"
          />
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Mínimo 1 h — máximo 168 h (7 días)
          </p>
        </div>

        <div className="space-y-1">
          <Label htmlFor={`channel_${index}`}>
            Canal <span className="text-destructive-600">*</span>
          </Label>
          <Select
            value={rule.channel}
            onValueChange={(val) => onUpdate(index, "channel", val as ReminderChannel)}
          >
            <SelectTrigger id={`channel_${index}`} aria-label="Canal de envío">
              <SelectValue />
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
      </div>

      {/* ── Message template ──────────────────────────────────────────────── */}
      <div className="space-y-1">
        <Label htmlFor={`message_template_${index}`}>
          Plantilla del mensaje <span className="text-destructive-600">*</span>
        </Label>
        <textarea
          id={`message_template_${index}`}
          rows={3}
          value={rule.message_template}
          onChange={(e) => onUpdate(index, "message_template", e.target.value)}
          className={cn(
            "flex w-full rounded-md border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm",
            "placeholder:text-[hsl(var(--muted-foreground))]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "resize-none",
          )}
          placeholder="Mensaje a enviar al paciente..."
          aria-label="Texto del recordatorio"
        />
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          Variables disponibles:{" "}
          <code className="text-xs font-mono bg-[hsl(var(--muted))] px-1 rounded">
            {"{{nombre}}"}
          </code>{" "}
          <code className="text-xs font-mono bg-[hsl(var(--muted))] px-1 rounded">
            {"{{clinica}}"}
          </code>{" "}
          <code className="text-xs font-mono bg-[hsl(var(--muted))] px-1 rounded">
            {"{{fecha}}"}
          </code>{" "}
          <code className="text-xs font-mono bg-[hsl(var(--muted))] px-1 rounded">
            {"{{hora}}"}
          </code>
        </p>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RemindersSettingsPage() {
  const { data: remindersConfig, isLoading } = useRemindersConfig();
  const { mutate: updateReminders, isPending } = useUpdateRemindersConfig();

  // Local state for the form — initialized from server data
  const [rules, setRules] = React.useState<ReminderRule[]>([]);
  const [defaultChannels, setDefaultChannels] = React.useState<ReminderChannel[]>([]);
  const [maxAllowed, setMaxAllowed] = React.useState<number>(3);

  // Sync server data into local state when it loads
  React.useEffect(() => {
    if (!remindersConfig) return;
    setRules(remindersConfig.rules);
    setDefaultChannels(remindersConfig.default_channels);
    setMaxAllowed(remindersConfig.max_reminders_allowed);
  }, [remindersConfig]);

  // ─── Rule handlers ────────────────────────────────────────────────────────

  function handleUpdateRule(index: number, field: keyof ReminderRule, value: unknown) {
    setRules((prev) =>
      prev.map((rule, i) => (i === index ? { ...rule, [field]: value } : rule)),
    );
  }

  function handleAddRule() {
    if (rules.length >= maxAllowed) return;
    setRules((prev) => [...prev, { ...DEFAULT_RULE }]);
  }

  function handleRemoveRule(index: number) {
    setRules((prev) => prev.filter((_, i) => i !== index));
  }

  // ─── Default channel handlers ─────────────────────────────────────────────

  function handleToggleChannel(channel: ReminderChannel, checked: boolean) {
    setDefaultChannels((prev) =>
      checked ? [...prev, channel] : prev.filter((c) => c !== channel),
    );
  }

  // ─── Submit ───────────────────────────────────────────────────────────────

  function handleSave() {
    updateReminders({
      rules,
      default_channels: defaultChannels,
      max_reminders_allowed: maxAllowed,
    });
  }

  // ─── Derived state ────────────────────────────────────────────────────────

  const canAddMore = rules.length < maxAllowed;

  if (isLoading) {
    return <RemindersSkeleton />;
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* ─── Page Header ──────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Recordatorios de citas
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Configura cuándo y cómo se envían los recordatorios automáticos a los pacientes.
        </p>
      </div>

      {/* ─── Default channels ─────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Canales predeterminados</CardTitle>
          <CardDescription>
            Canales activos cuando se agenda una cita sin regla específica.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <fieldset className="space-y-3" aria-label="Canales predeterminados">
            {CHANNEL_OPTIONS.map((opt) => {
              const isChecked = defaultChannels.includes(opt.value);
              return (
                <div key={opt.value} className="flex items-center gap-3">
                  <Checkbox
                    id={`default_channel_${opt.value}`}
                    checked={isChecked}
                    onCheckedChange={(checked) =>
                      handleToggleChannel(opt.value, Boolean(checked))
                    }
                    aria-label={`Canal ${CHANNEL_LABELS[opt.value]}`}
                  />
                  <Label
                    htmlFor={`default_channel_${opt.value}`}
                    className="cursor-pointer font-normal"
                  >
                    {opt.label}
                  </Label>
                </div>
              );
            })}
          </fieldset>
        </CardContent>
      </Card>

      {/* ─── Reminder rules ───────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">
                Reglas de recordatorio
                <span className="ml-2 text-sm font-normal text-[hsl(var(--muted-foreground))]">
                  ({rules.length} / {maxAllowed})
                </span>
              </CardTitle>
              <CardDescription>
                Define cuándo y por qué canal se envía cada recordatorio.
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddRule}
              disabled={!canAddMore}
              aria-label="Agregar regla de recordatorio"
            >
              <Plus className="mr-1 h-4 w-4" />
              Agregar
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {rules.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-[hsl(var(--muted))]">
                <Bell className="h-5 w-5 text-[hsl(var(--muted-foreground))]" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">Sin reglas configuradas</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                  Agrega al menos una regla para enviar recordatorios automáticos.
                </p>
              </div>
              {canAddMore && (
                <Button type="button" variant="outline" size="sm" onClick={handleAddRule}>
                  <Plus className="mr-1 h-4 w-4" />
                  Agregar primera regla
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {rules.map((rule, idx) => (
                <React.Fragment key={idx}>
                  {idx > 0 && <Separator />}
                  <ReminderRuleCard
                    rule={rule}
                    index={idx}
                    onUpdate={handleUpdateRule}
                    onRemove={handleRemoveRule}
                    canRemove={rules.length > 1}
                  />
                </React.Fragment>
              ))}
            </div>
          )}

          {!canAddMore && (
            <p className="text-xs text-[hsl(var(--muted-foreground))] text-center pt-1">
              Has alcanzado el límite de {maxAllowed} reglas de tu plan actual.
            </p>
          )}
        </CardContent>
      </Card>

      {/* ─── Save button ───────────────────────────────────────────────────── */}
      <div className="flex justify-end">
        <Button type="button" onClick={handleSave} disabled={isPending}>
          {isPending ? "Guardando..." : "Guardar configuración"}
        </Button>
      </div>
    </div>
  );
}
