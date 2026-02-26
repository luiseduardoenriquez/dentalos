"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Lock, Grid3X3, ChevronRight } from "lucide-react";
import Link from "next/link";
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
import { useSettings, useUpdateSettings } from "@/lib/hooks/use-settings";
import { useAuth } from "@/lib/hooks/use-auth";
import { cn } from "@/lib/utils";

// ─── Options ──────────────────────────────────────────────────────────────────

const TIMEZONES = [
  { value: "America/Bogota", label: "Bogotá (UTC-5)" },
  { value: "America/Lima", label: "Lima (UTC-5)" },
  { value: "America/Guayaquil", label: "Guayaquil (UTC-5)" },
  { value: "America/Santiago", label: "Santiago (UTC-4)" },
  { value: "America/Buenos_Aires", label: "Buenos Aires (UTC-3)" },
  { value: "America/Mexico_City", label: "Ciudad de México (UTC-6)" },
  { value: "America/Caracas", label: "Caracas (UTC-4)" },
];

const CURRENCIES = [
  { value: "COP", label: "Peso colombiano (COP)" },
  { value: "USD", label: "Dólar estadounidense (USD)" },
  { value: "MXN", label: "Peso mexicano (MXN)" },
  { value: "PEN", label: "Sol peruano (PEN)" },
  { value: "CLP", label: "Peso chileno (CLP)" },
  { value: "ARS", label: "Peso argentino (ARS)" },
];

const LOCALES = [
  { value: "es-CO", label: "Español — Colombia" },
  { value: "es-MX", label: "Español — México" },
  { value: "es-PE", label: "Español — Perú" },
  { value: "es-CL", label: "Español — Chile" },
  { value: "es-419", label: "Español — Latinoamérica" },
];

// ─── Validation Schema ────────────────────────────────────────────────────────

const clinicSettingsSchema = z.object({
  name: z
    .string()
    .min(1, "El nombre de la clínica es requerido")
    .max(200, "El nombre no puede exceder 200 caracteres")
    .transform((v) => v.trim()),
  phone: z
    .string()
    .regex(/^\+?[0-9]{7,15}$/, "Teléfono inválido (ej: +573001234567 o 3001234567)")
    .optional()
    .or(z.literal(""))
    .transform((v) => (v === "" ? undefined : v)),
  address: z
    .string()
    .max(300, "La dirección no puede exceder 300 caracteres")
    .optional()
    .or(z.literal(""))
    .transform((v) => (v === "" ? undefined : v?.trim())),
  timezone: z.string().min(1, "La zona horaria es requerida"),
  currency_code: z.string().min(1, "La moneda es requerida"),
  locale: z.string().min(1, "El idioma/regional es requerido"),
});

type ClinicSettingsFormValues = z.infer<typeof clinicSettingsSchema>;

// ─── Form Field Error ─────────────────────────────────────────────────────────

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-xs text-destructive-600 dark:text-destructive-400">{message}</p>;
}

// ─── Settings Form Skeleton ───────────────────────────────────────────────────

function SettingsSkeleton() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div className="space-y-1">
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-4 w-80" />
      </div>
      {[1, 2].map((i) => (
        <div key={i} className="border rounded-xl p-6 space-y-4">
          <Skeleton className="h-5 w-36" />
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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ClinicSettingsPage() {
  const { has_role } = useAuth();
  const isOwner = has_role("clinic_owner");

  const { data: settings, isLoading } = useSettings();
  const { mutate: updateSettings, isPending } = useUpdateSettings();

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isDirty },
  } = useForm<ClinicSettingsFormValues>({
    resolver: zodResolver(clinicSettingsSchema),
  });

  // Pre-fill form when settings load
  React.useEffect(() => {
    if (!settings) return;
    reset({
      name: settings.name,
      phone: settings.phone ?? "",
      address: settings.address ?? "",
      timezone: settings.timezone,
      currency_code: settings.currency_code,
      locale: settings.locale,
    });
  }, [settings, reset]);

  function onSubmit(values: ClinicSettingsFormValues) {
    updateSettings(values);
  }

  if (isLoading) {
    return <SettingsSkeleton />;
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* ─── Page Header ──────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Configuración de la clínica
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Información general y preferencias de la clínica.
        </p>
      </div>

      {/* Read-only notice for non-owners */}
      {!isOwner && (
        <div className="flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
          <Lock className="h-4 w-4 shrink-0" />
          Solo el propietario de la clínica puede modificar esta configuración.
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-6">
        {/* ─── Section 1: Información general ────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Información general</CardTitle>
            <CardDescription>Nombre, teléfono y dirección de la clínica.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="name">
                Nombre de la clínica <span className="text-destructive-600">*</span>
              </Label>
              <Input
                id="name"
                placeholder="Ej: Clínica Dental Nueva Sonrisa"
                {...register("name")}
                disabled={!isOwner}
                aria-invalid={!!errors.name}
              />
              <FieldError message={errors.name?.message} />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="phone">Teléfono</Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="+576041234567"
                  {...register("phone")}
                  disabled={!isOwner}
                  aria-invalid={!!errors.phone}
                />
                <FieldError message={errors.phone?.message} />
              </div>
            </div>

            <div className="space-y-1">
              <Label htmlFor="address">Dirección</Label>
              <Input
                id="address"
                placeholder="Ej: Calle 72 # 10-34, Bogotá D.C."
                {...register("address")}
                disabled={!isOwner}
                aria-invalid={!!errors.address}
              />
              <FieldError message={errors.address?.message} />
            </div>
          </CardContent>
        </Card>

        {/* ─── Section 2: Preferencias ─────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Preferencias</CardTitle>
            <CardDescription>
              Zona horaria, moneda e idioma regional para la clínica.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Timezone */}
              <div className="space-y-1">
                <Label htmlFor="timezone">
                  Zona horaria <span className="text-destructive-600">*</span>
                </Label>
                <Select
                  defaultValue={settings?.timezone}
                  onValueChange={(val) =>
                    setValue("timezone", val, { shouldValidate: true, shouldDirty: true })
                  }
                  disabled={!isOwner}
                >
                  <SelectTrigger id="timezone" aria-label="Zona horaria">
                    <SelectValue placeholder="Selecciona zona horaria" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIMEZONES.map((tz) => (
                      <SelectItem key={tz.value} value={tz.value}>
                        {tz.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.timezone?.message} />
              </div>

              {/* Currency */}
              <div className="space-y-1">
                <Label htmlFor="currency_code">
                  Moneda <span className="text-destructive-600">*</span>
                </Label>
                <Select
                  defaultValue={settings?.currency_code}
                  onValueChange={(val) =>
                    setValue("currency_code", val, { shouldValidate: true, shouldDirty: true })
                  }
                  disabled={!isOwner}
                >
                  <SelectTrigger id="currency_code" aria-label="Moneda">
                    <SelectValue placeholder="Selecciona moneda" />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map((c) => (
                      <SelectItem key={c.value} value={c.value}>
                        {c.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.currency_code?.message} />
              </div>

              {/* Locale */}
              <div className="space-y-1">
                <Label htmlFor="locale">
                  Regional / Idioma <span className="text-destructive-600">*</span>
                </Label>
                <Select
                  defaultValue={settings?.locale}
                  onValueChange={(val) =>
                    setValue("locale", val, { shouldValidate: true, shouldDirty: true })
                  }
                  disabled={!isOwner}
                >
                  <SelectTrigger id="locale" aria-label="Regional">
                    <SelectValue placeholder="Selecciona regional" />
                  </SelectTrigger>
                  <SelectContent>
                    {LOCALES.map((l) => (
                      <SelectItem key={l.value} value={l.value}>
                        {l.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldError message={errors.locale?.message} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ─── Save Button ─────────────────────────────────────────────────── */}
        {isOwner && (
          <div className="flex justify-end">
            <Button type="submit" disabled={isPending || !isDirty}>
              {isPending ? "Guardando..." : "Guardar cambios"}
            </Button>
          </div>
        )}
      </form>

      {/* ─── Other settings sections ─────────────────────────────────────── */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">
          Otras configuraciones
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {/* Odontogram settings link card */}
          <Link
            href="/settings/odontogram"
            className={cn(
              "flex items-center gap-4 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-4",
              "hover:bg-[hsl(var(--muted))]/50 hover:border-primary-300 dark:hover:border-primary-700",
              "transition-colors duration-150 group",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600",
            )}
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-100 dark:bg-primary-900/30">
              <Grid3X3 className="h-4 w-4 text-primary-600 dark:text-primary-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground leading-none">
                Odontograma
              </p>
              <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))] truncate">
                Modo de vista, zoom predeterminado y colores de condiciones
              </p>
            </div>
            <ChevronRight className="h-4 w-4 shrink-0 text-[hsl(var(--muted-foreground))] group-hover:text-foreground transition-colors" />
          </Link>
        </div>
      </div>
    </div>
  );
}
