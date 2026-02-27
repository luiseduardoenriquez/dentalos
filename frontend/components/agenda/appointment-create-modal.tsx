"use client";

import * as React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CalendarPlus, Clock, User, Stethoscope, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useCreateAppointment } from "@/lib/hooks/use-appointments";
import { useSearchPatients, type PatientSearchResult } from "@/lib/hooks/use-patients";
import { useUsers } from "@/lib/hooks/use-users";
import {
  appointmentCreateSchema,
  type AppointmentCreateForm,
  APPOINTMENT_TYPES,
  APPOINTMENT_TYPE_LABELS,
  APPOINTMENT_TYPE_DURATIONS,
  type AppointmentType,
} from "@/lib/validations/appointment";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AppointmentCreateModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** ISO date string (YYYY-MM-DDTHH:MM) pre-filled from a calendar slot click */
  defaultDate?: string;
  defaultDoctorId?: string;
  doctors?: Array<{ id: string; full_name: string }>;
  /** Pre-filled patient — used when opened from the patient detail page */
  defaultPatientId?: string;
  defaultPatientName?: string;
}

// ─── Step labels ──────────────────────────────────────────────────────────────

const STEP_LABELS = [
  { step: 1, label: "Paciente y tipo" },
  { step: 2, label: "Horario" },
  { step: 3, label: "Confirmar" },
] as const;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * 3-tap appointment creation modal (spec FE-AG-02).
 *
 * Step 1: Select patient (search typeahead) + appointment type
 * Step 2: Select doctor + date/time (pre-filled from calendar slot click if provided)
 * Step 3: Review summary + optional notes + confirm
 *
 * Duration is auto-calculated from appointment type but remains user-editable
 * on step 3.
 *
 * @example
 * <AppointmentCreateModal
 *   open={open}
 *   onOpenChange={setOpen}
 *   defaultDate="2026-03-25T10:00"
 *   doctors={[{ id: "...", full_name: "Dr. García" }]}
 * />
 */
function AppointmentCreateModal({
  open,
  onOpenChange,
  defaultDate,
  defaultDoctorId,
  doctors = [],
  defaultPatientId,
  defaultPatientName,
}: AppointmentCreateModalProps) {
  // ─── Step state ───────────────────────────────────────────────────────────
  const [step, setStep] = React.useState(1);

  // ─── Patient search state ─────────────────────────────────────────────────
  const [patientQuery, setPatientQuery] = React.useState("");
  const [selectedPatient, setSelectedPatient] =
    React.useState<PatientSearchResult | null>(
      defaultPatientId && defaultPatientName
        ? {
            id: defaultPatientId,
            full_name: defaultPatientName,
            document_type: "",
            document_number: "",
            phone: null,
            is_active: true,
          }
        : null,
    );
  const [showPatientDropdown, setShowPatientDropdown] = React.useState(false);

  // ─── Refs ─────────────────────────────────────────────────────────────────
  const patientSearchRef = React.useRef<HTMLInputElement>(null);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  // ─── Hooks ────────────────────────────────────────────────────────────────
  const { mutate: createAppointment, isPending } = useCreateAppointment();
  const { data: searchResults = [], isLoading: isSearching } =
    useSearchPatients(patientQuery);

  // Fetch doctors from the tenant's users when none are passed via props
  const { data: usersData } = useUsers({ page: 1, page_size: 100 });
  const resolvedDoctors = React.useMemo(() => {
    if (doctors.length > 0) return doctors;
    if (!usersData?.items) return [];
    return usersData.items
      .filter((u) => (u.role === "doctor" || u.role === "clinic_owner") && u.is_active)
      .map((u) => ({ id: u.id, full_name: u.name }));
  }, [doctors, usersData]);

  // ─── Form ─────────────────────────────────────────────────────────────────
  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<AppointmentCreateForm>({
    resolver: zodResolver(appointmentCreateSchema),
    defaultValues: {
      patient_id: defaultPatientId ?? "",
      doctor_id: defaultDoctorId ?? "",
      start_time: defaultDate ?? "",
      type: "consultation",
      duration_minutes: APPOINTMENT_TYPE_DURATIONS.consultation,
      send_reminder: true,
    },
  });

  const watchedType = watch("type") as AppointmentType | undefined;
  const watchedScheduledAt = watch("start_time");
  const watchedDoctorId = watch("doctor_id");
  const watchedDurationMinutes = watch("duration_minutes");
  const watchedNotes = watch("notes");

  // ─── Auto-fill duration when type changes ─────────────────────────────────
  React.useEffect(() => {
    if (watchedType && watchedType in APPOINTMENT_TYPE_DURATIONS) {
      setValue(
        "duration_minutes",
        APPOINTMENT_TYPE_DURATIONS[watchedType as AppointmentType],
        { shouldValidate: false },
      );
    }
  }, [watchedType, setValue]);

  // ─── Set patient_id in form when patient selected ─────────────────────────
  React.useEffect(() => {
    if (selectedPatient) {
      setValue("patient_id", selectedPatient.id, { shouldValidate: true });
    } else {
      setValue("patient_id", "", { shouldValidate: false });
    }
  }, [selectedPatient, setValue]);

  // ─── Close dropdown on outside click ─────────────────────────────────────
  React.useEffect(() => {
    function handle_outside_click(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        patientSearchRef.current &&
        !patientSearchRef.current.contains(e.target as Node)
      ) {
        setShowPatientDropdown(false);
      }
    }
    document.addEventListener("mousedown", handle_outside_click);
    return () => document.removeEventListener("mousedown", handle_outside_click);
  }, []);

  // ─── Reset on close ───────────────────────────────────────────────────────
  React.useEffect(() => {
    if (!open) {
      setStep(1);
      setPatientQuery("");
      setSelectedPatient(
        defaultPatientId && defaultPatientName
          ? {
              id: defaultPatientId,
              full_name: defaultPatientName,
              document_type: "",
              document_number: "",
              phone: null,
              is_active: true,
            }
          : null,
      );
      setShowPatientDropdown(false);
      reset({
        patient_id: defaultPatientId ?? "",
        doctor_id: defaultDoctorId ?? "",
        start_time: defaultDate ?? "",
        type: "consultation",
        duration_minutes: APPOINTMENT_TYPE_DURATIONS.consultation,
        send_reminder: true,
      });
    }
  }, [open, defaultDate, defaultDoctorId, defaultPatientId, defaultPatientName, reset]);

  // ─── Helpers ──────────────────────────────────────────────────────────────

  function handle_patient_select(patient: PatientSearchResult) {
    setSelectedPatient(patient);
    setPatientQuery("");
    setShowPatientDropdown(false);
  }

  function handle_patient_clear() {
    setSelectedPatient(null);
    setPatientQuery("");
    setValue("patient_id", "", { shouldValidate: false });
    setTimeout(() => patientSearchRef.current?.focus(), 50);
  }

  function format_end_time(scheduledAt: string, durationMinutes: number): string {
    if (!scheduledAt) return "";
    const start = new Date(scheduledAt);
    if (isNaN(start.getTime())) return "";
    const end = new Date(start.getTime() + durationMinutes * 60_000);
    return end.toLocaleTimeString("es-CO", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }

  function format_scheduled_at(scheduledAt: string): string {
    if (!scheduledAt) return "";
    const d = new Date(scheduledAt);
    if (isNaN(d.getTime())) return scheduledAt;
    return d.toLocaleDateString("es-CO", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }

  function format_time(scheduledAt: string): string {
    if (!scheduledAt) return "";
    const d = new Date(scheduledAt);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString("es-CO", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }

  function get_doctor_name(doctorId: string): string {
    return resolvedDoctors.find((d) => d.id === doctorId)?.full_name ?? doctorId;
  }

  // ─── Step validation before advancing ────────────────────────────────────

  function can_advance_step_1(): boolean {
    return Boolean(selectedPatient) && Boolean(watchedType);
  }

  function can_advance_step_2(): boolean {
    if (!watchedDoctorId && resolvedDoctors.length > 0) return false;
    if (!watchedScheduledAt) return false;
    const d = new Date(watchedScheduledAt);
    return !isNaN(d.getTime()) && d > new Date();
  }

  // ─── Submit ───────────────────────────────────────────────────────────────

  function on_submit(values: AppointmentCreateForm) {
    // Convert datetime-local value ("2026-03-25T10:00") to full ISO string
    const start_time_iso = new Date(values.start_time).toISOString();
    createAppointment(
      { ...values, start_time: start_time_iso },
      { onSuccess: () => onOpenChange(false) },
    );
  }

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg w-full p-0 gap-0 overflow-hidden">
        {/* ─── Header ─────────────────────────────────────────────────────── */}
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-[hsl(var(--border))]">
          <DialogTitle className="flex items-center gap-2 text-lg font-bold">
            <CalendarPlus className="h-5 w-5 text-primary-600" />
            Nueva Cita
          </DialogTitle>
          <DialogDescription className="sr-only">
            Crea una nueva cita en 3 pasos: selecciona paciente y tipo, elige
            horario y doctor, luego confirma.
          </DialogDescription>

          {/* ─── Step indicator ─────────────────────────────────────────── */}
          <div className="flex items-center gap-1 mt-3" aria-label="Pasos del formulario">
            {STEP_LABELS.map(({ step: s, label }) => (
              <React.Fragment key={s}>
                <div
                  className={cn(
                    "flex items-center gap-1.5 text-xs font-medium transition-colors",
                    step >= s
                      ? "text-primary-600 dark:text-primary-400"
                      : "text-[hsl(var(--muted-foreground))]",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                      step > s
                        ? "bg-primary-600 text-white dark:bg-primary-500"
                        : step === s
                          ? "bg-primary-100 text-primary-700 border border-primary-400 dark:bg-primary-900/40 dark:text-primary-300"
                          : "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]",
                    )}
                  >
                    {step > s ? "✓" : s}
                  </span>
                  <span className="hidden sm:inline">{label}</span>
                </div>
                {s < STEP_LABELS.length && (
                  <div
                    className={cn(
                      "h-px flex-1 mx-1 transition-colors",
                      step > s
                        ? "bg-primary-400 dark:bg-primary-600"
                        : "bg-[hsl(var(--border))]",
                    )}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </DialogHeader>

        {/* ─── Form body ──────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit(on_submit)} noValidate>
          <div className="px-6 py-5 space-y-5 max-h-[calc(80vh-180px)] overflow-y-auto">

            {/* ─── STEP 1: Patient + type ──────────────────────────────── */}
            {step === 1 && (
              <div className="space-y-5">

                {/* Patient search */}
                <div className="space-y-2">
                  <Label className="text-sm font-semibold flex items-center gap-1.5">
                    <User className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
                    Paciente
                    <span className="text-destructive-600 dark:text-destructive-400">*</span>
                  </Label>

                  {selectedPatient ? (
                    /* Selected patient chip */
                    <div className="flex items-center gap-2 rounded-full border border-primary-300 bg-primary-50 dark:border-primary-700 dark:bg-primary-950/50 px-3 py-1.5 w-fit max-w-full">
                      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-600 text-white text-xs font-bold">
                        {selectedPatient.full_name.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-sm font-medium text-primary-800 dark:text-primary-200 truncate max-w-[200px]">
                        {selectedPatient.full_name}
                      </span>
                      {selectedPatient.document_number && (
                        <span className="text-xs text-primary-500 dark:text-primary-400 shrink-0">
                          {selectedPatient.document_type} {selectedPatient.document_number}
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={handle_patient_clear}
                        aria-label="Quitar paciente seleccionado"
                        className="ml-1 shrink-0 rounded-full p-0.5 text-primary-500 hover:bg-primary-200 hover:text-primary-700 dark:hover:bg-primary-800 dark:hover:text-primary-300 transition-colors"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    /* Search input + dropdown */
                    <div className="relative">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[hsl(var(--muted-foreground))] pointer-events-none" />
                        <Input
                          ref={patientSearchRef}
                          type="text"
                          value={patientQuery}
                          onChange={(e) => {
                            setPatientQuery(e.target.value);
                            setShowPatientDropdown(true);
                          }}
                          onFocus={() => setShowPatientDropdown(true)}
                          placeholder="Buscar por nombre o cédula..."
                          className="pl-9"
                          autoComplete="off"
                          aria-label="Buscar paciente"
                          aria-expanded={showPatientDropdown}
                          aria-haspopup="listbox"
                        />
                        {isSearching && (
                          <div className="absolute right-3 top-1/2 -translate-y-1/2">
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
                          </div>
                        )}
                      </div>

                      {/* Results dropdown */}
                      {showPatientDropdown && patientQuery.length >= 2 && (
                        <div
                          ref={dropdownRef}
                          role="listbox"
                          aria-label="Resultados de búsqueda de pacientes"
                          className={cn(
                            "absolute z-50 mt-1 w-full rounded-md border border-[hsl(var(--border))]",
                            "bg-[hsl(var(--background))] shadow-lg",
                            "max-h-52 overflow-y-auto",
                          )}
                        >
                          {searchResults.length === 0 && !isSearching && (
                            <div className="px-4 py-3 text-sm text-[hsl(var(--muted-foreground))] text-center">
                              Sin resultados para &quot;{patientQuery}&quot;
                            </div>
                          )}
                          {searchResults.map((patient) => (
                            <button
                              key={patient.id}
                              type="button"
                              role="option"
                              aria-selected={false}
                              onClick={() => handle_patient_select(patient)}
                              className={cn(
                                "w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm",
                                "hover:bg-[hsl(var(--muted))] focus:bg-[hsl(var(--muted))]",
                                "focus:outline-none transition-colors",
                                !patient.is_active && "opacity-50",
                              )}
                            >
                              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold">
                                {patient.full_name.charAt(0).toUpperCase()}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="font-medium text-foreground truncate">
                                  {patient.full_name}
                                </div>
                                <div className="text-xs text-[hsl(var(--muted-foreground))]">
                                  {patient.document_type} {patient.document_number}
                                  {patient.phone && ` · ${patient.phone}`}
                                </div>
                              </div>
                              {!patient.is_active && (
                                <span className="text-xs text-amber-600 dark:text-amber-400 shrink-0">
                                  Inactivo
                                </span>
                              )}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {errors.patient_id && (
                    <p className="text-xs text-destructive-600 dark:text-destructive-400">
                      {errors.patient_id.message}
                    </p>
                  )}
                </div>

                {/* Appointment type */}
                <div className="space-y-2">
                  <Label className="text-sm font-semibold flex items-center gap-1.5">
                    <Stethoscope className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
                    Tipo de cita
                    <span className="text-destructive-600 dark:text-destructive-400">*</span>
                  </Label>

                  <div className="grid grid-cols-2 gap-2">
                    {APPOINTMENT_TYPES.map((type) => (
                      <Controller
                        key={type}
                        name="type"
                        control={control}
                        render={({ field }) => (
                          <button
                            type="button"
                            onClick={() => field.onChange(type)}
                            className={cn(
                              "flex flex-col items-start gap-0.5 rounded-lg border px-3 py-2.5",
                              "text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-2",
                              field.value === type
                                ? "border-primary-400 bg-primary-50 text-primary-800 dark:border-primary-600 dark:bg-primary-950/50 dark:text-primary-200"
                                : "border-[hsl(var(--border))] bg-[hsl(var(--background))] text-foreground hover:border-primary-300 hover:bg-[hsl(var(--muted))]",
                            )}
                            aria-pressed={field.value === type}
                          >
                            <span className="font-semibold">
                              {APPOINTMENT_TYPE_LABELS[type]}
                            </span>
                            <span className="text-xs font-normal text-[hsl(var(--muted-foreground))]">
                              {APPOINTMENT_TYPE_DURATIONS[type]} min
                            </span>
                          </button>
                        )}
                      />
                    ))}
                  </div>

                  {errors.type && (
                    <p className="text-xs text-destructive-600 dark:text-destructive-400">
                      {errors.type.message}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* ─── STEP 2: Doctor + date/time ──────────────────────────── */}
            {step === 2 && (
              <div className="space-y-5">

                {/* Doctor select — shown only when doctors are available */}
                {resolvedDoctors.length > 0 && (
                  <div className="space-y-2">
                    <Label
                      htmlFor="doctor_id"
                      className="text-sm font-semibold flex items-center gap-1.5"
                    >
                      <User className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
                      Doctor
                      <span className="text-destructive-600 dark:text-destructive-400">*</span>
                    </Label>
                    <Controller
                      name="doctor_id"
                      control={control}
                      render={({ field }) => (
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <SelectTrigger id="doctor_id" aria-label="Selecciona doctor">
                            <SelectValue placeholder="Selecciona un doctor" />
                          </SelectTrigger>
                          <SelectContent>
                            {resolvedDoctors.map((d) => (
                              <SelectItem key={d.id} value={d.id}>
                                {d.full_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.doctor_id && (
                      <p className="text-xs text-destructive-600 dark:text-destructive-400">
                        {errors.doctor_id.message}
                      </p>
                    )}
                  </div>
                )}

                {/* Date + time */}
                <div className="space-y-2">
                  <Label
                    htmlFor="start_time"
                    className="text-sm font-semibold flex items-center gap-1.5"
                  >
                    <Clock className="h-3.5 w-3.5 text-[hsl(var(--muted-foreground))]" />
                    Fecha y hora
                    <span className="text-destructive-600 dark:text-destructive-400">*</span>
                  </Label>
                  <Input
                    id="start_time"
                    type="datetime-local"
                    min={new Date().toISOString().slice(0, 16)}
                    {...register("start_time")}
                    className="w-full"
                    aria-invalid={Boolean(errors.start_time)}
                  />
                  {errors.start_time && (
                    <p className="text-xs text-destructive-600 dark:text-destructive-400">
                      {errors.start_time.message}
                    </p>
                  )}
                </div>

                {/* Duration — pre-filled from type, user-editable */}
                <div className="space-y-2">
                  <Label
                    htmlFor="duration_minutes"
                    className="text-sm font-semibold"
                  >
                    Duración (minutos)
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="duration_minutes"
                      type="number"
                      min={10}
                      max={240}
                      step={5}
                      {...register("duration_minutes", { valueAsNumber: true })}
                      className="w-32"
                      aria-invalid={Boolean(errors.duration_minutes)}
                    />
                    <span className="text-xs text-[hsl(var(--muted-foreground))] bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800 rounded-full px-2.5 py-1 font-medium">
                      Estimado para {watchedType ? APPOINTMENT_TYPE_LABELS[watchedType as AppointmentType] : "este tipo"}
                    </span>
                  </div>
                  {errors.duration_minutes && (
                    <p className="text-xs text-destructive-600 dark:text-destructive-400">
                      {errors.duration_minutes.message}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* ─── STEP 3: Review + notes ──────────────────────────────── */}
            {step === 3 && (
              <div className="space-y-5">

                {/* Summary card */}
                <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--muted))]/40 p-4 space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                    Resumen de la cita
                  </p>

                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-[hsl(var(--muted-foreground))]">Paciente</span>
                      <span className="font-medium text-right">
                        {selectedPatient?.full_name ?? "—"}
                      </span>
                    </div>

                    {resolvedDoctors.length > 0 && watchedDoctorId && (
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-[hsl(var(--muted-foreground))]">Doctor</span>
                        <span className="font-medium text-right">
                          {get_doctor_name(watchedDoctorId)}
                        </span>
                      </div>
                    )}

                    <div className="flex items-center justify-between gap-4">
                      <span className="text-[hsl(var(--muted-foreground))]">Tipo</span>
                      <span className="font-medium">
                        {watchedType
                          ? APPOINTMENT_TYPE_LABELS[watchedType as AppointmentType]
                          : "—"}
                      </span>
                    </div>

                    {watchedScheduledAt && (
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-[hsl(var(--muted-foreground))]">Fecha</span>
                        <span className="font-medium text-right">
                          {format_scheduled_at(watchedScheduledAt)}
                        </span>
                      </div>
                    )}

                    {watchedScheduledAt && (
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-[hsl(var(--muted-foreground))]">Hora</span>
                        <span className="font-medium">
                          {format_time(watchedScheduledAt)}
                          {" – "}
                          {format_end_time(watchedScheduledAt, watchedDurationMinutes ?? 30)}
                          {" "}
                          <span className="text-[hsl(var(--muted-foreground))] font-normal">
                            ({watchedDurationMinutes} min)
                          </span>
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Notes — optional */}
                <div className="space-y-2">
                  <Label htmlFor="notes" className="text-sm font-semibold">
                    Notas adicionales{" "}
                    <span className="text-[hsl(var(--muted-foreground))] font-normal">
                      (opcional)
                    </span>
                  </Label>
                  <textarea
                    id="notes"
                    rows={3}
                    placeholder="Motivo de consulta, observaciones..."
                    {...register("notes")}
                    className="w-full resize-none rounded-md border border-[hsl(var(--input))] bg-[hsl(var(--background))] px-3 py-2 text-sm placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-0"
                    aria-invalid={Boolean(errors.notes)}
                  />
                  <div className="flex items-center justify-between text-xs text-[hsl(var(--muted-foreground))]">
                    <span>
                      {errors.notes
                        ? errors.notes.message
                        : "Máximo 500 caracteres"}
                    </span>
                    <span className="tabular-nums">
                      {(watchedNotes ?? "").length}/500
                    </span>
                  </div>
                </div>

                {/* Reminder toggle */}
                <div className="flex items-center gap-3">
                  <Controller
                    name="send_reminder"
                    control={control}
                    render={({ field }) => (
                      <button
                        type="button"
                        role="switch"
                        aria-checked={field.value}
                        onClick={() => field.onChange(!field.value)}
                        className={cn(
                          "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors",
                          "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-2",
                          field.value
                            ? "bg-primary-600"
                            : "bg-[hsl(var(--muted))]",
                        )}
                      >
                        <span
                          className={cn(
                            "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform",
                            field.value ? "translate-x-4" : "translate-x-0",
                          )}
                        />
                      </button>
                    )}
                  />
                  <span className="text-sm text-foreground">
                    Enviar recordatorio al paciente
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* ─── Footer ─────────────────────────────────────────────────────── */}
          <DialogFooter className="px-6 py-4 border-t border-[hsl(var(--border))] flex items-center justify-between gap-3">
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  if (step === 1) {
                    onOpenChange(false);
                  } else {
                    setStep((s) => s - 1);
                  }
                }}
                disabled={isPending}
              >
                {step === 1 ? "Cancelar" : "Atrás"}
              </Button>
            </div>

            <div className="flex gap-2">
              {step < 3 ? (
                <Button
                  type="button"
                  onClick={() => setStep((s) => s + 1)}
                  disabled={
                    (step === 1 && !can_advance_step_1()) ||
                    (step === 2 && !can_advance_step_2())
                  }
                >
                  Siguiente
                </Button>
              ) : (
                <Button type="submit" disabled={isPending} className="min-w-[140px]">
                  {isPending ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Agendando...
                    </span>
                  ) : (
                    "Confirmar Cita"
                  )}
                </Button>
              )}
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

AppointmentCreateModal.displayName = "AppointmentCreateModal";

export { AppointmentCreateModal };
