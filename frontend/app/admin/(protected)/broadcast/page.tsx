"use client";

import { useState } from "react";
import {
  useBroadcastHistory,
  useSendBroadcast,
  type BroadcastHistoryItem,
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
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
import { toast } from "sonner";
import { Send, Radio, AlertCircle, Users } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Constants ─────────────────────────────────────────────────────────────────

const TEMPLATE_OPTIONS = [
  { value: "welcome", label: "Bienvenida" },
  { value: "feature_update", label: "Actualización" },
  { value: "payment_reminder", label: "Recordatorio de pago" },
  { value: "compliance_alert", label: "Alerta de cumplimiento" },
] as const;

const PLAN_OPTIONS = [
  { value: "free", label: "Free" },
  { value: "starter", label: "Starter" },
  { value: "pro", label: "Pro" },
  { value: "clinica", label: "Clínica" },
  { value: "enterprise", label: "Enterprise" },
] as const;

const COUNTRY_OPTIONS = [
  { value: "CO", label: "Colombia" },
  { value: "MX", label: "México" },
  { value: "PE", label: "Perú" },
  { value: "CL", label: "Chile" },
  { value: "AR", label: "Argentina" },
] as const;

const STATUS_OPTIONS = [
  { value: "active", label: "Activa" },
  { value: "trial", label: "Prueba" },
  { value: "suspended", label: "Suspendida" },
] as const;

// Template badge color classes
const TEMPLATE_BADGE_CLASSES: Record<string, string> = {
  welcome:
    "border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300",
  feature_update:
    "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300",
  payment_reminder:
    "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300",
  compliance_alert:
    "border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300",
};

const TEMPLATE_LABELS: Record<string, string> = {
  welcome: "Bienvenida",
  feature_update: "Actualización",
  payment_reminder: "Recordatorio de pago",
  compliance_alert: "Alerta de cumplimiento",
};

const COUNTRY_LABELS: Record<string, string> = {
  CO: "Colombia",
  MX: "México",
  PE: "Perú",
  CL: "Chile",
  AR: "Argentina",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Activa",
  trial: "Prueba",
  suspended: "Suspendida",
};

const PLAN_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter",
  pro: "Pro",
  clinica: "Clínica",
  enterprise: "Enterprise",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("es-419", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

// ─── Template Badge ────────────────────────────────────────────────────────────

function TemplateBadge({ template }: { template: string | null }) {
  if (!template) {
    return (
      <span className="text-sm text-[hsl(var(--muted-foreground))]">—</span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        TEMPLATE_BADGE_CLASSES[template] ??
          "border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300",
      )}
    >
      {TEMPLATE_LABELS[template] ?? template}
    </span>
  );
}

// ─── Filter Pills ──────────────────────────────────────────────────────────────

interface FilterPillsProps {
  plan: string | null;
  country: string | null;
  status: string | null;
}

function FilterPills({ plan, country, status }: FilterPillsProps) {
  const pills: { label: string; value: string }[] = [];

  if (plan) pills.push({ label: "Plan", value: PLAN_LABELS[plan] ?? plan });
  if (country)
    pills.push({ label: "País", value: COUNTRY_LABELS[country] ?? country });
  if (status)
    pills.push({
      label: "Estado",
      value: STATUS_LABELS[status] ?? status,
    });

  if (pills.length === 0) {
    return (
      <span className="text-sm text-[hsl(var(--muted-foreground))]">
        Todos
      </span>
    );
  }

  return (
    <div className="flex flex-wrap gap-1">
      {pills.map((pill) => (
        <span
          key={pill.label}
          className="inline-flex items-center gap-1 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-2 py-0.5 text-xs text-[hsl(var(--muted-foreground))]"
        >
          <span className="font-medium text-[hsl(var(--foreground))]">
            {pill.label}:
          </span>
          {pill.value}
        </span>
      ))}
    </div>
  );
}

// ─── History Loading Skeleton ──────────────────────────────────────────────────

function HistoryLoadingSkeleton() {
  return (
    <div className="divide-y divide-[hsl(var(--border))]">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex items-center gap-4 px-6 py-4">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-5 w-28 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-4 w-8 ml-2" />
          <Skeleton className="h-4 w-32 ml-auto" />
          <Skeleton className="h-4 w-28" />
        </div>
      ))}
    </div>
  );
}

// ─── History Table ─────────────────────────────────────────────────────────────

interface HistoryTableProps {
  items: BroadcastHistoryItem[];
  isLoading: boolean;
}

function HistoryTable({ items, isLoading }: HistoryTableProps) {
  if (isLoading) {
    return <HistoryLoadingSkeleton />;
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <Radio className="h-10 w-10 text-[hsl(var(--muted-foreground))] opacity-40" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Aún no se han enviado broadcasts. Usa el formulario de arriba para
          enviar el primero.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="min-w-[200px]">Asunto</TableHead>
            <TableHead className="whitespace-nowrap">Plantilla</TableHead>
            <TableHead>Filtros</TableHead>
            <TableHead className="whitespace-nowrap text-right">
              Destinatarios
            </TableHead>
            <TableHead className="whitespace-nowrap">Enviado por</TableHead>
            <TableHead className="whitespace-nowrap">Fecha</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id}>
              {/* Asunto */}
              <TableCell className="max-w-[260px]">
                <p
                  className="text-sm font-medium truncate"
                  title={item.subject}
                >
                  {item.subject}
                </p>
              </TableCell>

              {/* Plantilla */}
              <TableCell>
                <TemplateBadge template={item.template} />
              </TableCell>

              {/* Filtros */}
              <TableCell className="min-w-[140px]">
                <FilterPills
                  plan={item.filter_plan}
                  country={item.filter_country}
                  status={item.filter_status}
                />
              </TableCell>

              {/* Destinatarios */}
              <TableCell className="text-right">
                <span className="inline-flex items-center gap-1 text-sm font-medium tabular-nums">
                  <Users className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
                  {item.recipients_count.toLocaleString("es-419")}
                </span>
              </TableCell>

              {/* Enviado por */}
              <TableCell className="text-sm text-[hsl(var(--muted-foreground))] max-w-[160px] truncate">
                {item.sent_by}
              </TableCell>

              {/* Fecha */}
              <TableCell className="text-sm text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                {formatDate(item.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ─── Send Form State ───────────────────────────────────────────────────────────

interface SendFormState {
  subject: string;
  body: string;
  template: string;
  filter_plan: string;
  filter_country: string;
  filter_status: string;
}

const EMPTY_FORM: SendFormState = {
  subject: "",
  body: "",
  template: "",
  filter_plan: "",
  filter_country: "",
  filter_status: "",
};

// ─── Validation ────────────────────────────────────────────────────────────────

function isFormValid(form: SendFormState): boolean {
  return form.subject.trim().length >= 2 && form.body.trim().length >= 10;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminBroadcastPage() {
  const [form, setForm] = useState<SendFormState>(EMPTY_FORM);
  const [historyPage, setHistoryPage] = useState(1);

  const sendBroadcast = useSendBroadcast();
  const { data: historyData, isLoading: historyLoading, isError: historyError, refetch: refetchHistory } =
    useBroadcastHistory(historyPage);

  const items = historyData?.items ?? [];
  const total = historyData?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  function handleChange(updates: Partial<SendFormState>) {
    setForm((prev) => ({ ...prev, ...updates }));
  }

  function handleSend() {
    if (!isFormValid(form) || sendBroadcast.isPending) return;

    const payload: {
      subject: string;
      body: string;
      template?: string;
      filter_plan?: string;
      filter_country?: string;
      filter_status?: string;
    } = {
      subject: form.subject.trim(),
      body: form.body.trim(),
    };

    if (form.template) payload.template = form.template;
    if (form.filter_plan) payload.filter_plan = form.filter_plan;
    if (form.filter_country) payload.filter_country = form.filter_country;
    if (form.filter_status) payload.filter_status = form.filter_status;

    sendBroadcast.mutate(payload, {
      onSuccess: (data) => {
        toast.success(
          `Broadcast enviado a ${data.recipients_count.toLocaleString("es-419")} destinatarios.`,
        );
        setForm(EMPTY_FORM);
      },
      onError: () => {
        toast.error("No se pudo enviar el broadcast. Intenta de nuevo.");
      },
    });
  }

  const valid = isFormValid(form);
  const subjectTooShort = form.subject.trim().length > 0 && form.subject.trim().length < 2;
  const bodyTooShort = form.body.trim().length > 0 && form.body.trim().length < 10;

  return (
    <div className="flex flex-col gap-6">
      {/* ── Page header ── */}
      <div>
        <div className="flex items-center gap-2">
          <Radio className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          <h1 className="text-2xl font-bold tracking-tight">Broadcast</h1>
        </div>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Enviar mensajes masivos a propietarios de clínicas
        </p>
      </div>

      {/* ── Send form ── */}
      <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Nuevo Broadcast</CardTitle>
          <CardDescription>
            Redacta y envía un mensaje a los propietarios de clínicas. Usa los
            filtros para segmentar los destinatarios.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Subject */}
          <div className="space-y-1.5">
            <Label htmlFor="bc-subject">
              Asunto <span className="text-red-500">*</span>
            </Label>
            <Input
              id="bc-subject"
              type="text"
              value={form.subject}
              onChange={(e) => handleChange({ subject: e.target.value })}
              placeholder="ej: Actualización importante de la plataforma"
              className={cn("text-sm", subjectTooShort && "border-red-400 focus-visible:ring-red-400")}
              aria-describedby={subjectTooShort ? "bc-subject-error" : undefined}
            />
            {subjectTooShort && (
              <p id="bc-subject-error" className="text-xs text-red-500">
                El asunto debe tener al menos 2 caracteres.
              </p>
            )}
          </div>

          {/* Body */}
          <div className="space-y-1.5">
            <Label htmlFor="bc-body">
              Mensaje <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="bc-body"
              rows={5}
              value={form.body}
              onChange={(e) => handleChange({ body: e.target.value })}
              placeholder="Escribe el contenido del mensaje que recibirán los propietarios de clínicas..."
              className={cn(
                "resize-y text-sm",
                bodyTooShort && "border-red-400 focus-visible:ring-red-400",
              )}
              aria-describedby={bodyTooShort ? "bc-body-error" : undefined}
            />
            {bodyTooShort && (
              <p id="bc-body-error" className="text-xs text-red-500">
                El mensaje debe tener al menos 10 caracteres.
              </p>
            )}
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              {form.body.length} caracteres
            </p>
          </div>

          {/* Template selector */}
          <div className="space-y-1.5">
            <Label htmlFor="bc-template">
              Plantilla{" "}
              <span className="text-[hsl(var(--muted-foreground))]">
                (opcional)
              </span>
            </Label>
            <Select
              value={form.template || "__none__"}
              onValueChange={(val) =>
                handleChange({ template: val === "__none__" ? "" : val })
              }
            >
              <SelectTrigger id="bc-template" className="text-sm">
                <SelectValue placeholder="Sin plantilla" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">Sin plantilla</SelectItem>
                {TEMPLATE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              La plantilla determina el estilo visual del email.
            </p>
          </div>

          {/* Filters row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Plan filter */}
            <div className="space-y-1.5">
              <Label htmlFor="bc-plan">
                Plan{" "}
                <span className="text-[hsl(var(--muted-foreground))]">
                  (opcional)
                </span>
              </Label>
              <Select
                value={form.filter_plan || "__all__"}
                onValueChange={(val) =>
                  handleChange({
                    filter_plan: val === "__all__" ? "" : val,
                  })
                }
              >
                <SelectTrigger id="bc-plan" className="text-sm">
                  <SelectValue placeholder="Todos los planes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">Todos los planes</SelectItem>
                  {PLAN_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Country filter */}
            <div className="space-y-1.5">
              <Label htmlFor="bc-country">
                País{" "}
                <span className="text-[hsl(var(--muted-foreground))]">
                  (opcional)
                </span>
              </Label>
              <Select
                value={form.filter_country || "__all__"}
                onValueChange={(val) =>
                  handleChange({
                    filter_country: val === "__all__" ? "" : val,
                  })
                }
              >
                <SelectTrigger id="bc-country" className="text-sm">
                  <SelectValue placeholder="Todos los países" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">Todos los países</SelectItem>
                  {COUNTRY_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Status filter */}
            <div className="space-y-1.5">
              <Label htmlFor="bc-status">
                Estado{" "}
                <span className="text-[hsl(var(--muted-foreground))]">
                  (opcional)
                </span>
              </Label>
              <Select
                value={form.filter_status || "__all__"}
                onValueChange={(val) =>
                  handleChange({
                    filter_status: val === "__all__" ? "" : val,
                  })
                }
              >
                <SelectTrigger id="bc-status" className="text-sm">
                  <SelectValue placeholder="Todos los estados" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">Todos los estados</SelectItem>
                  {STATUS_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Active filter summary */}
          {(form.filter_plan || form.filter_country || form.filter_status) && (
            <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--muted)/0.4)] px-4 py-3">
              <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide mb-2">
                Segmentación activa
              </p>
              <FilterPills
                plan={form.filter_plan || null}
                country={form.filter_country || null}
                status={form.filter_status || null}
              />
            </div>
          )}

          {/* Submit */}
          <div className="flex items-center justify-end pt-1">
            <Button
              onClick={handleSend}
              disabled={!valid || sendBroadcast.isPending}
              className="gap-2"
            >
              <Send className="h-4 w-4" />
              {sendBroadcast.isPending ? "Enviando..." : "Enviar Broadcast"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ── History section ── */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">Historial de Envíos</h2>
          {total > 0 && (
            <span className="text-sm text-[hsl(var(--muted-foreground))]">
              {total} {total === 1 ? "envío" : "envíos"} en total
            </span>
          )}
        </div>

        {/* Error state */}
        {historyError && !historyLoading && (
          <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
              <AlertCircle className="h-8 w-8 text-[hsl(var(--muted-foreground))]" />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Error al cargar el historial. Verifica la conexión con la API.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchHistory()}
              >
                Reintentar
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Table card */}
        {!historyError && (
          <Card className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
            <CardContent className="p-0">
              <HistoryTable items={items} isLoading={historyLoading} />
            </CardContent>
          </Card>
        )}

        {/* Pagination */}
        {!historyError && !historyLoading && total > 20 && (
          <div className="flex items-center justify-between text-sm text-[hsl(var(--muted-foreground))]">
            <span>
              Página {historyPage} de {totalPages}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={historyPage <= 1}
                onClick={() => setHistoryPage((p) => Math.max(1, p - 1))}
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={historyPage >= totalPages}
                onClick={() =>
                  setHistoryPage((p) => Math.min(totalPages, p + 1))
                }
              >
                Siguiente
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
