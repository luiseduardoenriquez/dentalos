"use client";

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Bell, AlertCircle } from "lucide-react";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { apiGet, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";
import { EmptyState } from "@/components/empty-state";

// ─── Types ────────────────────────────────────────────────────────────────────

type ReminderChannel = "sms" | "email" | "whatsapp";

interface ReminderRule {
  hours_before: number;
  channels: ReminderChannel[];
}

interface RemindersConfig {
  reminders: ReminderRule[];
  default_channels: ReminderChannel[];
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

const DEFAULT_REMINDER: ReminderRule = {
  hours_before: 24,
  channels: ["whatsapp"],
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
        </div>
      ))}
    </div>
  );
}

// ─── Reminder Rule Card ───────────────────────────────────────────────────────

interface ReminderRuleCardProps {
  rule: ReminderRule;
  index: number;
  onUpdateHours: (index: number, hours: number) => void;
  onToggleChannel: (index: number, channel: ReminderChannel, checked: boolean) => void;
  onRemove: (index: number) => void;
  canRemove: boolean;
}

function ReminderRuleCard({
  rule,
  index,
  onUpdateHours,
  onToggleChannel,
  onRemove,
  canRemove,
}: ReminderRuleCardProps) {
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

      {/* ── Hours before ──────────────────────────────────────────────────── */}
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
          onChange={(e) => onUpdateHours(index, Number(e.target.value))}
          className="max-w-[200px]"
          aria-label="Horas antes de la cita"
        />
        <p className="text-xs text-[hsl(var(--muted-foreground))]">
          Mínimo 1 h — máximo 168 h (7 días)
        </p>
      </div>

      {/* ── Channels (multi-select checkboxes) ────────────────────────────── */}
      <div className="space-y-2">
        <Label>
          Canales <span className="text-destructive-600">*</span>
        </Label>
        <fieldset className="space-y-2" aria-label={`Canales para recordatorio ${index + 1}`}>
          {CHANNEL_OPTIONS.map((opt) => {
            const isChecked = rule.channels.includes(opt.value);
            return (
              <div key={opt.value} className="flex items-center gap-3">
                <Checkbox
                  id={`reminder_${index}_channel_${opt.value}`}
                  checked={isChecked}
                  onCheckedChange={(checked) =>
                    onToggleChannel(index, opt.value, Boolean(checked))
                  }
                  aria-label={`Canal ${CHANNEL_LABELS[opt.value]}`}
                />
                <Label
                  htmlFor={`reminder_${index}_channel_${opt.value}`}
                  className="cursor-pointer font-normal"
                >
                  {opt.label}
                </Label>
              </div>
            );
          })}
        </fieldset>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RemindersSettingsPage() {
  const { data: remindersConfig, isLoading, isError } = useRemindersConfig();
  const { mutate: updateReminders, isPending } = useUpdateRemindersConfig();

  // Local state for the form — initialized from server data
  const [reminders, setReminders] = React.useState<ReminderRule[]>([]);
  const [defaultChannels, setDefaultChannels] = React.useState<ReminderChannel[]>([]);
  const [maxAllowed, setMaxAllowed] = React.useState<number>(3);

  // Sync server data into local state when it loads
  React.useEffect(() => {
    if (!remindersConfig) return;
    setReminders(remindersConfig.reminders ?? []);
    setDefaultChannels(remindersConfig.default_channels ?? []);
    setMaxAllowed(remindersConfig.max_reminders_allowed ?? 3);
  }, [remindersConfig]);

  // ─── Reminder handlers ──────────────────────────────────────────────────────

  function handleUpdateHours(index: number, hours: number) {
    setReminders((prev) =>
      prev.map((r, i) => (i === index ? { ...r, hours_before: hours } : r)),
    );
  }

  function handleToggleReminderChannel(
    index: number,
    channel: ReminderChannel,
    checked: boolean,
  ) {
    setReminders((prev) =>
      prev.map((r, i) => {
        if (i !== index) return r;
        const channels = checked
          ? [...r.channels, channel]
          : r.channels.filter((c) => c !== channel);
        return { ...r, channels };
      }),
    );
  }

  function handleAddReminder() {
    if (reminders.length >= maxAllowed) return;
    setReminders((prev) => [...prev, { ...DEFAULT_REMINDER, channels: [...DEFAULT_REMINDER.channels] }]);
  }

  function handleRemoveReminder(index: number) {
    setReminders((prev) => prev.filter((_, i) => i !== index));
  }

  // ─── Default channel handlers ─────────────────────────────────────────────

  function handleToggleDefaultChannel(channel: ReminderChannel, checked: boolean) {
    setDefaultChannels((prev) =>
      checked ? [...prev, channel] : prev.filter((c) => c !== channel),
    );
  }

  // ─── Submit ───────────────────────────────────────────────────────────────

  function handleSave() {
    updateReminders({
      reminders,
      default_channels: defaultChannels,
      max_reminders_allowed: maxAllowed,
    });
  }

  // ─── Derived state ────────────────────────────────────────────────────────

  const canAddMore = reminders.length < maxAllowed;

  if (isLoading) {
    return <RemindersSkeleton />;
  }

  if (isError) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Error al cargar recordatorios"
        description="No se pudo cargar la configuración de recordatorios. Intenta de nuevo."
      />
    );
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
                      handleToggleDefaultChannel(opt.value, Boolean(checked))
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
                  ({reminders.length} / {maxAllowed})
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
              onClick={handleAddReminder}
              disabled={!canAddMore}
              aria-label="Agregar regla de recordatorio"
            >
              <Plus className="mr-1 h-4 w-4" />
              Agregar
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {reminders.length === 0 ? (
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
                <Button type="button" variant="outline" size="sm" onClick={handleAddReminder}>
                  <Plus className="mr-1 h-4 w-4" />
                  Agregar primera regla
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {reminders.map((rule, idx) => (
                <React.Fragment key={idx}>
                  {idx > 0 && <Separator />}
                  <ReminderRuleCard
                    rule={rule}
                    index={idx}
                    onUpdateHours={handleUpdateHours}
                    onToggleChannel={handleToggleReminderChannel}
                    onRemove={handleRemoveReminder}
                    canRemove={reminders.length > 1}
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
