"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CalendarDays,
  TrendingUp,
  AlertTriangle,
  Gift,
  RefreshCw,
  Clock,
  Printer,
  DollarSign,
  UserX,
  Users,
} from "lucide-react";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface HuddleAppointment {
  id: string;
  patient_id: string;
  patient_name: string;
  doctor_name: string;
  start_time: string;
  duration_minutes: number;
  appointment_type: string;
  status: string;
}

interface ProductionGoals {
  daily_target: number;
  daily_actual: number;
  weekly_target: number;
  weekly_actual: number;
  monthly_target: number;
  monthly_actual: number;
}

interface IncompletePlan {
  id: string;
  patient_id: string;
  patient_name: string;
  title: string;
  pending_procedures: number;
  estimated_value: number;
}

interface OutstandingBalance {
  patient_id: string;
  patient_name: string;
  balance: number;
  overdue: boolean;
  days_overdue: number | null;
}

interface BirthdayPatient {
  patient_id: string;
  patient_name: string;
  age: number;
  phone: string | null;
}

interface RecallPatient {
  patient_id: string;
  patient_name: string;
  last_visit: string;
  days_overdue: number;
  phone: string | null;
}

interface HuddleData {
  today_appointments: HuddleAppointment[];
  production_goals: ProductionGoals;
  incomplete_plans: IncompletePlan[];
  outstanding_balances: OutstandingBalance[];
  birthday_patients: BirthdayPatient[];
  recall_due_patients: RecallPatient[];
  yesterday_collections: number;
  no_show_count: number;
  no_show_rate: number;
}

// ─── Status labels ────────────────────────────────────────────────────────────

const APPT_STATUS_LABELS: Record<string, string> = {
  scheduled: "Programada",
  confirmed: "Confirmada",
  in_progress: "En curso",
  completed: "Completada",
  cancelled: "Cancelada",
  no_show: "No asistió",
};

const APPT_STATUS_VARIANTS: Record<string, "default" | "secondary" | "success" | "destructive"> = {
  scheduled: "default",
  confirmed: "default",
  in_progress: "default",
  completed: "success",
  cancelled: "secondary",
  no_show: "destructive",
};

// ─── Production goal bar ──────────────────────────────────────────────────────

function GoalBar({
  label,
  actual,
  target,
}: {
  label: string;
  actual: number;
  target: number;
}) {
  const pct = target > 0 ? Math.min((actual / target) * 100, 100) : 0;
  const color =
    pct >= 100 ? "bg-green-500" : pct >= 70 ? "bg-primary-500" : "bg-yellow-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-[hsl(var(--muted-foreground))]">{label}</span>
        <span className="tabular-nums font-medium">
          {formatCurrency(actual)}{" "}
          <span className="text-xs text-[hsl(var(--muted-foreground))]">
            / {formatCurrency(target)}
          </span>
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-[hsl(var(--muted))]">
        <div
          className={cn("h-2 rounded-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="print:shadow-none print:border-gray-300">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="h-4 w-4 text-primary-600" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function HuddleSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-9 w-28" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-48 rounded-xl" />
        ))}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HuddlePage() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["huddle"],
    queryFn: () => apiGet<HuddleData>("/huddle/today"),
    refetchInterval: 300_000,
    staleTime: 60_000,
  });

  const today = new Intl.DateTimeFormat("es-419", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date());

  if (isLoading) return <HuddleSkeleton />;

  // Gracefully degrade to empty state when API is unavailable
  const huddle: HuddleData = data ?? {
    today_appointments: [],
    production_goals: { daily_target: 0, daily_actual: 0, weekly_target: 0, weekly_actual: 0, monthly_target: 0, monthly_actual: 0 },
    incomplete_plans: [],
    outstanding_balances: [],
    birthday_patients: [],
    recall_due_patients: [],
    yesterday_collections: 0,
    no_show_count: 0,
    no_show_rate: 0,
  };

  return (
    <div className="space-y-6 print:space-y-4">
      {/* ─── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between print:hidden">
        <div>
          <h1 className="text-2xl font-bold text-foreground capitalize">{today}</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Resumen del día — Morning Huddle
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={cn("h-4 w-4 mr-1", isFetching && "animate-spin")} />
            Actualizar
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            <Printer className="h-4 w-4 mr-1" />
            Imprimir
          </Button>
        </div>
      </div>

      {/* ─── Print header ────────────────────────────────────────────────── */}
      <div className="hidden print:block">
        <h1 className="text-xl font-bold capitalize">{today} — Morning Huddle</h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2 print:grid-cols-2">
        {/* ─── 1. Citas de hoy ──────────────────────────────────────────── */}
        <Section icon={CalendarDays} title={`Citas de hoy (${huddle.today_appointments.length})`}>
          {huddle.today_appointments.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
              No hay citas programadas para hoy.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Hora</TableHead>
                  <TableHead>Paciente</TableHead>
                  <TableHead>Doctor</TableHead>
                  <TableHead>Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {huddle.today_appointments.map((appt) => {
                  const time = new Date(appt.start_time).toLocaleTimeString("es-CO", {
                    hour: "2-digit",
                    minute: "2-digit",
                  });
                  return (
                    <TableRow key={appt.id}>
                      <TableCell className="text-sm tabular-nums font-medium">{time}</TableCell>
                      <TableCell className="text-sm">
                        <Link
                          href={`/patients/${appt.patient_id}`}
                          className="text-primary-600 hover:underline print:no-underline print:text-foreground"
                        >
                          {appt.patient_name}
                        </Link>
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {appt.doctor_name}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={APPT_STATUS_VARIANTS[appt.status] ?? "default"}
                          className="text-xs"
                        >
                          {APPT_STATUS_LABELS[appt.status] ?? appt.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Section>

        {/* ─── 2. Metas de producción ───────────────────────────────────── */}
        <Section icon={TrendingUp} title="Metas de producción">
          <div className="space-y-4">
            <GoalBar
              label="Diaria"
              actual={huddle.production_goals.daily_actual}
              target={huddle.production_goals.daily_target}
            />
            <GoalBar
              label="Semanal"
              actual={huddle.production_goals.weekly_actual}
              target={huddle.production_goals.weekly_target}
            />
            <GoalBar
              label="Mensual"
              actual={huddle.production_goals.monthly_actual}
              target={huddle.production_goals.monthly_target}
            />
          </div>
        </Section>

        {/* ─── 3. Planes incompletos ────────────────────────────────────── */}
        <Section icon={Clock} title="Planes de tratamiento pendientes (top 10)">
          {huddle.incomplete_plans.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
              No hay planes de tratamiento pendientes.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Paciente</TableHead>
                  <TableHead className="text-right">Procedimientos</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {huddle.incomplete_plans.slice(0, 10).map((plan) => (
                  <TableRow key={plan.id}>
                    <TableCell className="text-sm">
                      <Link
                        href={`/patients/${plan.patient_id}`}
                        className="text-primary-600 hover:underline print:text-foreground print:no-underline"
                      >
                        {plan.patient_name}
                      </Link>
                      <p className="text-xs text-[hsl(var(--muted-foreground))] truncate max-w-[140px]">
                        {plan.title}
                      </p>
                    </TableCell>
                    <TableCell className="text-sm text-right tabular-nums">
                      {plan.pending_procedures}
                    </TableCell>
                    <TableCell className="text-sm text-right tabular-nums font-medium">
                      {formatCurrency(plan.estimated_value)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Section>

        {/* ─── 4. Saldos pendientes ─────────────────────────────────────── */}
        <Section icon={DollarSign} title="Saldos pendientes (top 10)">
          {huddle.outstanding_balances.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
              No hay saldos pendientes.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Paciente</TableHead>
                  <TableHead className="text-right">Saldo</TableHead>
                  <TableHead>Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {huddle.outstanding_balances.slice(0, 10).map((bal) => (
                  <TableRow key={bal.patient_id}>
                    <TableCell className="text-sm">
                      <Link
                        href={`/patients/${bal.patient_id}`}
                        className="text-primary-600 hover:underline print:text-foreground print:no-underline"
                      >
                        {bal.patient_name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm text-right tabular-nums font-medium">
                      {formatCurrency(bal.balance)}
                    </TableCell>
                    <TableCell>
                      {bal.overdue ? (
                        <Badge variant="destructive" className="text-xs">
                          Vencido {bal.days_overdue}d
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="text-xs">
                          Pendiente
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Section>

        {/* ─── 5. Cumpleaños ────────────────────────────────────────────── */}
        <Section icon={Gift} title={`Cumpleaños hoy (${huddle.birthday_patients.length})`}>
          {huddle.birthday_patients.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
              No hay cumpleaños hoy.
            </p>
          ) : (
            <ul className="space-y-2">
              {huddle.birthday_patients.map((p) => (
                <li key={p.patient_id} className="flex items-center justify-between text-sm">
                  <Link
                    href={`/patients/${p.patient_id}`}
                    className="text-primary-600 hover:underline print:text-foreground print:no-underline"
                  >
                    {p.patient_name}
                  </Link>
                  <span className="text-[hsl(var(--muted-foreground))]">
                    {p.age} años
                    {p.phone && (
                      <span className="ml-2 text-xs">{p.phone}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* ─── 6. Recall vencido ────────────────────────────────────────── */}
        <Section icon={Users} title={`Pacientes por recordar (${huddle.recall_due_patients.length})`}>
          {huddle.recall_due_patients.length === 0 ? (
            <p className="text-sm text-[hsl(var(--muted-foreground))] text-center py-4">
              No hay pacientes con recall vencido.
            </p>
          ) : (
            <ul className="space-y-2">
              {huddle.recall_due_patients.slice(0, 10).map((p) => (
                <li key={p.patient_id} className="flex items-center justify-between text-sm">
                  <Link
                    href={`/patients/${p.patient_id}`}
                    className="text-primary-600 hover:underline print:text-foreground print:no-underline"
                  >
                    {p.patient_name}
                  </Link>
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    Última visita: {formatDate(p.last_visit)} ({p.days_overdue}d)
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* ─── 7. Recaudo de ayer ───────────────────────────────────────── */}
        <Card className="print:shadow-none print:border-gray-300">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <DollarSign className="h-4 w-4 text-primary-600" />
              Recaudo de ayer
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold tabular-nums text-green-600">
              {formatCurrency(huddle.yesterday_collections)}
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
              Total recaudado el día anterior.
            </p>
          </CardContent>
        </Card>

        {/* ─── 8. No-show ───────────────────────────────────────────────── */}
        <Card className="print:shadow-none print:border-gray-300">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <UserX className="h-4 w-4 text-orange-500" />
              Inasistencias recientes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold tabular-nums">
              {huddle.no_show_count}
            </p>
            <p className="text-sm mt-1">
              Tasa de inasistencia:{" "}
              <span
                className={cn(
                  "font-semibold",
                  huddle.no_show_rate > 15 ? "text-red-600" : "text-foreground",
                )}
              >
                {huddle.no_show_rate.toFixed(1)}%
              </span>
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
              Últimos 30 días.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
