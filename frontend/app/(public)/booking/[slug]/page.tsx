"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CalendarCheck2, CheckCircle2, ChevronLeft, ChevronRight, Loader2, Stethoscope } from "lucide-react";
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
import {
  useBookingConfig,
  useCreatePublicBooking,
  type PublicBookingResponse,
} from "@/lib/hooks/use-public-booking";
import { cn } from "@/lib/utils";

// ─── Validation Schema ────────────────────────────────────────────────────────

const bookingSchema = z.object({
  // Step 1: service selection
  doctor_id: z.string().min(1, "Selecciona un doctor"),
  appointment_type: z.string().min(1, "Selecciona el tipo de cita"),
  // Step 2: date/time
  start_time: z
    .string()
    .min(1, "Selecciona la fecha y hora de tu cita")
    .refine((v) => !isNaN(Date.parse(v)), { message: "Fecha y hora inválidas" }),
  // Step 3: patient info
  patient_name: z
    .string()
    .min(2, "El nombre debe tener al menos 2 caracteres")
    .max(200, "El nombre no puede exceder 200 caracteres")
    .transform((v) => v.trim()),
  patient_phone: z
    .string()
    .regex(/^\+?[0-9]{7,15}$/, "Teléfono inválido (ej: +573001234567 o 3001234567)")
    .transform((v) => v.trim()),
  patient_email: z
    .string()
    .email("Correo electrónico inválido")
    .optional()
    .or(z.literal(""))
    .transform((v) => (v === "" ? null : v)),
  notes: z
    .string()
    .max(500, "Las notas no pueden exceder 500 caracteres")
    .optional()
    .or(z.literal(""))
    .transform((v) => (v === "" ? null : v?.trim())),
});

type BookingFormValues = z.infer<typeof bookingSchema>;

// ─── Step indicator ───────────────────────────────────────────────────────────

interface StepIndicatorProps {
  current: 1 | 2 | 3;
}

const STEPS = [
  { id: 1, label: "Servicio" },
  { id: 2, label: "Fecha y hora" },
  { id: 3, label: "Tus datos" },
];

function StepIndicator({ current }: StepIndicatorProps) {
  return (
    <nav aria-label="Pasos del formulario" className="mb-8">
      <ol className="flex items-center justify-center gap-0">
        {STEPS.map((step, idx) => {
          const isDone = step.id < current;
          const isActive = step.id === current;
          return (
            <React.Fragment key={step.id}>
              <li className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold transition-colors",
                    isActive
                      ? "bg-primary-600 text-white"
                      : isDone
                        ? "bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
                        : "bg-slate-100 text-slate-400 dark:bg-zinc-800 dark:text-zinc-500",
                  )}
                  aria-current={isActive ? "step" : undefined}
                >
                  {isDone ? <CheckCircle2 className="h-4 w-4" /> : step.id}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium",
                    isActive
                      ? "text-primary-600 dark:text-primary-400"
                      : isDone
                        ? "text-slate-600 dark:text-slate-400"
                        : "text-slate-400 dark:text-zinc-500",
                  )}
                >
                  {step.label}
                </span>
              </li>
              {idx < STEPS.length - 1 && (
                <div
                  className={cn(
                    "h-0.5 w-12 mt-[-16px] mx-1 transition-colors",
                    step.id < current
                      ? "bg-primary-300 dark:bg-primary-700"
                      : "bg-slate-200 dark:bg-zinc-700",
                  )}
                  aria-hidden="true"
                />
              )}
            </React.Fragment>
          );
        })}
      </ol>
    </nav>
  );
}

// ─── Field error helper ───────────────────────────────────────────────────────

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-xs text-destructive-600 dark:text-destructive-400">{message}</p>;
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function BookingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <Skeleton className="h-7 w-56 mx-auto" />
        <Skeleton className="h-4 w-40 mx-auto" />
      </div>
      <div className="space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
      <Skeleton className="h-10 w-full" />
    </div>
  );
}

// ─── Confirmation screen ──────────────────────────────────────────────────────

interface ConfirmationProps {
  booking: PublicBookingResponse;
  clinicName: string;
}

function BookingConfirmation({ booking, clinicName }: ConfirmationProps) {
  const formattedDate = React.useMemo(() => {
    try {
      return new Intl.DateTimeFormat("es-419", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(booking.start_time));
    } catch {
      return booking.start_time;
    }
  }, [booking.start_time]);

  return (
    <div className="text-center space-y-6 py-4">
      <div className="flex justify-center">
        <div className="flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30">
          <CheckCircle2 className="w-8 h-8 text-green-600 dark:text-green-400" />
        </div>
      </div>

      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-foreground">¡Cita solicitada!</h2>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Tu solicitud fue recibida por {clinicName}.
        </p>
      </div>

      <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--muted))] px-6 py-4 text-left space-y-3">
        <div className="flex items-start gap-3">
          <CalendarCheck2 className="h-4 w-4 text-primary-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Fecha y hora</p>
            <p className="text-sm font-medium text-foreground capitalize">{formattedDate}</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <Stethoscope className="h-4 w-4 text-primary-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Doctor</p>
            <p className="text-sm font-medium text-foreground">{booking.doctor_name}</p>
          </div>
        </div>
      </div>

      <p className="text-xs text-[hsl(var(--muted-foreground))]">
        Código de confirmación:{" "}
        <span className="font-mono font-semibold text-foreground">{booking.appointment_id}</span>
      </p>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PublicBookingPage() {
  const params = useParams<{ slug: string }>();
  const slug = params?.slug ?? "";

  const { data: config, isLoading: isLoadingConfig, isError: isConfigError } = useBookingConfig(slug);
  const { mutate: createBooking, isPending: isSubmitting } = useCreatePublicBooking(slug);

  const [step, setStep] = React.useState<1 | 2 | 3>(1);
  const [confirmation, setConfirmation] = React.useState<PublicBookingResponse | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    trigger,
    formState: { errors },
  } = useForm<BookingFormValues>({
    resolver: zodResolver(bookingSchema),
    defaultValues: {
      doctor_id: "",
      appointment_type: "",
      start_time: "",
      patient_name: "",
      patient_phone: "",
      patient_email: "",
      notes: "",
    },
  });

  // Advance from step 1 to 2
  async function handleNextFromStep1() {
    const valid = await trigger(["doctor_id", "appointment_type"]);
    if (valid) setStep(2);
  }

  // Advance from step 2 to 3
  async function handleNextFromStep2() {
    const valid = await trigger(["start_time"]);
    if (valid) setStep(3);
  }

  function onSubmit(values: BookingFormValues) {
    createBooking(
      {
        patient_name: values.patient_name,
        patient_phone: values.patient_phone,
        patient_email: values.patient_email ?? null,
        doctor_id: values.doctor_id,
        appointment_type: values.appointment_type,
        start_time: values.start_time,
        notes: values.notes ?? null,
      },
      {
        onSuccess: (data) => {
          setConfirmation(data);
        },
      },
    );
  }

  // ─── Error state ────────────────────────────────────────────────────────────
  if (isConfigError) {
    return (
      <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8 text-center space-y-3">
        <p className="text-sm font-medium text-foreground">Página no encontrada</p>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          No encontramos una clínica con ese enlace. Verifica la dirección e inténtalo de nuevo.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-white dark:bg-zinc-900 shadow-sm p-8">
      {/* ─── Clinic name ──────────────────────────────────────────────────── */}
      {isLoadingConfig ? (
        <div className="text-center mb-6 space-y-2">
          <Skeleton className="h-6 w-48 mx-auto" />
          <Skeleton className="h-4 w-32 mx-auto" />
        </div>
      ) : config ? (
        <div className="text-center mb-6">
          <h1 className="text-xl font-semibold text-foreground">{config.clinic_name}</h1>
          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
            Solicita tu cita en línea
          </p>
        </div>
      ) : null}

      {/* ─── Confirmation screen ───────────────────────────────────────────── */}
      {confirmation ? (
        <BookingConfirmation booking={confirmation} clinicName={config?.clinic_name ?? ""} />
      ) : isLoadingConfig ? (
        <BookingSkeleton />
      ) : config ? (
        <>
          <StepIndicator current={step} />

          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            {/* ═══ Step 1: Doctor + appointment type ════════════════════════ */}
            {step === 1 && (
              <div className="space-y-5">
                <Card>
                  <CardHeader className="pb-4">
                    <CardTitle className="text-base">Selecciona el servicio</CardTitle>
                    <CardDescription>
                      Elige el doctor y el tipo de cita que necesitas.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Doctor select */}
                    <div className="space-y-1">
                      <Label htmlFor="doctor_id">
                        Doctor <span className="text-destructive-600">*</span>
                      </Label>
                      <Select
                        onValueChange={(val) =>
                          setValue("doctor_id", val, { shouldValidate: true, shouldDirty: true })
                        }
                      >
                        <SelectTrigger id="doctor_id" aria-invalid={!!errors.doctor_id}>
                          <SelectValue placeholder="Selecciona un doctor" />
                        </SelectTrigger>
                        <SelectContent>
                          {config.doctors.map((doctor) => (
                            <SelectItem key={doctor.id} value={doctor.id}>
                              {doctor.full_name}
                              {doctor.specialties.length > 0 && (
                                <span className="ml-1 text-xs text-[hsl(var(--muted-foreground))]">
                                  — {doctor.specialties.join(", ")}
                                </span>
                              )}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FieldError message={errors.doctor_id?.message} />
                    </div>

                    {/* Appointment type select */}
                    <div className="space-y-1">
                      <Label htmlFor="appointment_type">
                        Tipo de cita <span className="text-destructive-600">*</span>
                      </Label>
                      <Select
                        onValueChange={(val) =>
                          setValue("appointment_type", val, {
                            shouldValidate: true,
                            shouldDirty: true,
                          })
                        }
                      >
                        <SelectTrigger id="appointment_type" aria-invalid={!!errors.appointment_type}>
                          <SelectValue placeholder="Selecciona el tipo de cita" />
                        </SelectTrigger>
                        <SelectContent>
                          {config.appointment_types.map((appt) => (
                            <SelectItem key={appt.type} value={appt.type}>
                              {appt.label}
                              <span className="ml-1 text-xs text-[hsl(var(--muted-foreground))]">
                                ({appt.duration} min)
                              </span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FieldError message={errors.appointment_type?.message} />
                    </div>
                  </CardContent>
                </Card>

                <div className="flex justify-end">
                  <Button type="button" onClick={handleNextFromStep1}>
                    Continuar
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {/* ═══ Step 2: Date and time ════════════════════════════════════ */}
            {step === 2 && (
              <div className="space-y-5">
                <Card>
                  <CardHeader className="pb-4">
                    <CardTitle className="text-base">Fecha y hora</CardTitle>
                    <CardDescription>
                      Elige cuándo quieres tu cita.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-1">
                      <Label htmlFor="start_time">
                        Fecha y hora <span className="text-destructive-600">*</span>
                      </Label>
                      <Input
                        id="start_time"
                        type="datetime-local"
                        {...register("start_time")}
                        aria-invalid={!!errors.start_time}
                        className="w-full"
                      />
                      <FieldError message={errors.start_time?.message} />
                    </div>

                    {/* Working hours reference */}
                    {Object.entries(config.working_hours).some(([, v]) => v !== null) && (
                      <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--muted))] p-3">
                        <p className="text-xs font-medium text-foreground mb-2">
                          Horario de atención:
                        </p>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                          {Object.entries(config.working_hours).map(([day, hours]) => {
                            const dayLabels: Record<string, string> = {
                              monday: "Lunes",
                              tuesday: "Martes",
                              wednesday: "Miércoles",
                              thursday: "Jueves",
                              friday: "Viernes",
                              saturday: "Sábado",
                              sunday: "Domingo",
                            };
                            return (
                              <div key={day} className="flex justify-between text-xs">
                                <span className="text-[hsl(var(--muted-foreground))]">
                                  {dayLabels[day] ?? day}
                                </span>
                                <span
                                  className={cn(
                                    "font-medium",
                                    hours
                                      ? "text-foreground"
                                      : "text-[hsl(var(--muted-foreground))]",
                                  )}
                                >
                                  {hours ? `${hours.start} – ${hours.end}` : "Cerrado"}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <div className="flex justify-between">
                  <Button type="button" variant="outline" onClick={() => setStep(1)}>
                    <ChevronLeft className="mr-1 h-4 w-4" />
                    Atrás
                  </Button>
                  <Button type="button" onClick={handleNextFromStep2}>
                    Continuar
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {/* ═══ Step 3: Patient info ════════════════════════════════════ */}
            {step === 3 && (
              <div className="space-y-5">
                <Card>
                  <CardHeader className="pb-4">
                    <CardTitle className="text-base">Tus datos</CardTitle>
                    <CardDescription>
                      Ingresa tu información de contacto para confirmar la cita.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Full name */}
                    <div className="space-y-1">
                      <Label htmlFor="patient_name">
                        Nombre completo <span className="text-destructive-600">*</span>
                      </Label>
                      <Input
                        id="patient_name"
                        type="text"
                        placeholder="Ej: Ana María Gómez"
                        autoComplete="name"
                        {...register("patient_name")}
                        aria-invalid={!!errors.patient_name}
                      />
                      <FieldError message={errors.patient_name?.message} />
                    </div>

                    {/* Phone */}
                    <div className="space-y-1">
                      <Label htmlFor="patient_phone">
                        Teléfono <span className="text-destructive-600">*</span>
                      </Label>
                      <Input
                        id="patient_phone"
                        type="tel"
                        placeholder="+573001234567"
                        autoComplete="tel"
                        {...register("patient_phone")}
                        aria-invalid={!!errors.patient_phone}
                      />
                      <FieldError message={errors.patient_phone?.message} />
                    </div>

                    {/* Email (optional) */}
                    <div className="space-y-1">
                      <Label htmlFor="patient_email">Correo electrónico</Label>
                      <Input
                        id="patient_email"
                        type="email"
                        placeholder="correo@ejemplo.com (opcional)"
                        autoComplete="email"
                        {...register("patient_email")}
                        aria-invalid={!!errors.patient_email}
                      />
                      <FieldError message={errors.patient_email?.message} />
                    </div>

                    {/* Notes (optional) */}
                    <div className="space-y-1">
                      <Label htmlFor="notes">Notas adicionales</Label>
                      <textarea
                        id="notes"
                        rows={3}
                        placeholder="¿Algo que el doctor deba saber? (opcional)"
                        className={cn(
                          "flex w-full rounded-md border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm",
                          "placeholder:text-[hsl(var(--muted-foreground))]",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2",
                          "disabled:cursor-not-allowed disabled:opacity-50",
                          "resize-none",
                        )}
                        {...register("notes")}
                        aria-invalid={!!errors.notes}
                      />
                      <FieldError message={errors.notes?.message} />
                    </div>
                  </CardContent>
                </Card>

                <div className="flex justify-between">
                  <Button type="button" variant="outline" onClick={() => setStep(2)}>
                    <ChevronLeft className="mr-1 h-4 w-4" />
                    Atrás
                  </Button>
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                        Enviando...
                      </>
                    ) : (
                      "Solicitar cita"
                    )}
                  </Button>
                </div>
              </div>
            )}
          </form>
        </>
      ) : null}
    </div>
  );
}
