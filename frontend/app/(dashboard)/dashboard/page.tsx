"use client";

import Link from "next/link";
import {
  Users,
  CalendarDays,
  ClipboardList,
  DollarSign,
  UserPlus,
  ArrowRight,
  TrendingUp,
  GitPullRequestArrow,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/hooks/use-auth";
import { useAnalyticsDashboard } from "@/lib/hooks/use-analytics";
import { useIncomingReferrals, useUpdateReferral } from "@/lib/hooks/use-referrals";
import { cn, formatCurrency } from "@/lib/utils";

// ─── KPI Card ─────────────────────────────────────────────────────────────────

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
  trend?: string;
}

function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconColor,
  iconBg,
  trend,
}: KpiCardProps) {
  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          <div
            className={cn(
              "flex items-center justify-center w-9 h-9 rounded-lg flex-shrink-0",
              iconBg,
            )}
            aria-hidden="true"
          >
            <Icon className={cn("h-4 w-4", iconColor)} />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold text-foreground tabular-nums">{value}</p>
        {subtitle && (
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        )}
        {trend && (
          <div className="mt-2 flex items-center gap-1 text-xs text-success-600 dark:text-success-500">
            <TrendingUp className="h-3 w-3" aria-hidden="true" />
            <span>{trend}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── KPI data ─────────────────────────────────────────────────────────────────
// Computed dynamically inside the component — see DashboardPage.

// ─── Quick Actions ────────────────────────────────────────────────────────────

interface QuickAction {
  label: string;
  description: string;
  href: string;
  icon: React.ElementType;
  variant: "primary" | "secondary" | "outline";
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    label: "Nuevo paciente",
    description: "Registra un nuevo paciente en la clínica",
    href: "/patients/new",
    icon: UserPlus,
    variant: "primary",
  },
  {
    label: "Agendar cita",
    description: "Programa una nueva cita",
    href: "/agenda",
    icon: CalendarDays,
    variant: "outline",
  },
];

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <Card className="border-dashed">
      <CardContent className="py-12">
        <div className="flex flex-col items-center text-center gap-4 max-w-sm mx-auto">
          {/* Illustration */}
          <div className="relative">
            <div className="w-20 h-20 rounded-2xl bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center">
              <Users className="h-10 w-10 text-primary-300 dark:text-primary-700" aria-hidden="true" />
            </div>
            <div
              className="absolute -top-1 -right-1 w-7 h-7 rounded-full bg-primary-600 flex items-center justify-center shadow-md"
              aria-hidden="true"
            >
              <span className="text-white text-xs font-bold">+</span>
            </div>
          </div>

          <div>
            <h3 className="text-base font-semibold text-foreground">
              Comienza registrando tu primer paciente
            </h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              Agrega un paciente para empezar a gestionar su historia clínica,
              odontograma, citas y tratamientos desde DentalOS.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 w-full">
            <Button asChild className="flex-1">
              <Link href="/patients/new">
                <UserPlus className="h-4 w-4" aria-hidden="true" />
                Registrar paciente
              </Link>
            </Button>
            <Button asChild variant="outline" className="flex-1">
              <Link href="/patients">
                Ver pacientes
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Referral Widget ──────────────────────────────────────────────────────────

function ReferralWidget() {
  const { data, isLoading } = useIncomingReferrals(1, 5);
  const updateReferral = useUpdateReferral();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <GitPullRequestArrow className="h-4 w-4 text-primary-600" />
            Referencias recibidas
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.total === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <GitPullRequestArrow className="h-4 w-4 text-primary-600" />
            Referencias pendientes
          </CardTitle>
          <span className="text-xs font-medium px-2 py-1 rounded-full bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400">
            {data.total}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {data.items.map((ref) => (
            <div
              key={ref.id}
              className="flex items-start justify-between gap-3 p-3 rounded-lg border border-border bg-card"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground truncate">
                  De: {ref.from_doctor_name ?? "Doctor"}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                  {ref.reason}
                </p>
                {ref.priority === "urgent" && (
                  <span className="inline-block mt-1 text-[10px] font-medium px-1.5 py-0.5 rounded bg-destructive-100 text-destructive-700 dark:bg-destructive-900/30 dark:text-destructive-400">
                    Urgente
                  </span>
                )}
              </div>
              <div className="flex gap-1.5 shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  onClick={() =>
                    updateReferral.mutate({
                      referralId: ref.id,
                      status: "declined",
                    })
                  }
                  disabled={updateReferral.isPending}
                >
                  Rechazar
                </Button>
                <Button
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() =>
                    updateReferral.mutate({
                      referralId: ref.id,
                      status: "accepted",
                    })
                  }
                  disabled={updateReferral.isPending}
                >
                  Aceptar
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * Dashboard home page.
 *
 * Shows:
 * - Personalized welcome greeting with user name and clinic name.
 * - 4 KPI summary cards (patient count, today's appointments, pending treatments, monthly revenue).
 * - Quick action buttons.
 * - Empty state with CTA to register first patient.
 *
 * All values are placeholder zeros — data wiring will happen in Sprint 3-4
 * when the respective API endpoints are implemented.
 */
export default function DashboardPage() {
  const { user, tenant } = useAuthStore();

  // Derive first name from full name for the greeting
  const firstName = user?.name?.split(" ")[0] ?? "Doctor";

  const { data: dashboard, isLoading: dashboardLoading } = useAnalyticsDashboard("month");
  const role = user?.role;

  // ── Role-based welcome subtitle ──────────────────────────────────────────
  let welcomeSubtitle: React.ReactNode;
  const clinicName = tenant?.name || "tu clínica";
  if (role === "clinic_owner") {
    welcomeSubtitle = (
      <>
        Panel de{" "}
        <span className="font-medium text-foreground">{clinicName}</span>
        {" "}— aquí tienes el resumen de hoy.
      </>
    );
  } else if (role === "doctor") {
    welcomeSubtitle = (
      <>
        Tu resumen personal —{" "}
        <span className="font-medium text-foreground">{clinicName}</span>.
      </>
    );
  } else {
    welcomeSubtitle = (
      <>
        Panel de{" "}
        <span className="font-medium text-foreground">{clinicName}</span>.
      </>
    );
  }

  // ── Dynamic KPI cards ────────────────────────────────────────────────────
  const patientTotal = dashboard?.patients.total ?? 0;
  const newPatients = dashboard?.patients.new_in_period ?? 0;
  const patientGrowth = dashboard?.patients.growth_percentage ?? 0;
  const todayAppointments = dashboard?.appointments.today_count ?? 0;
  const pendingTreatments = (dashboard?.appointments.period_total ?? 0) - (dashboard?.appointments.completed ?? 0);
  const monthRevenue = dashboard?.revenue.collected ?? 0;
  const revenueGrowth = dashboard?.revenue.growth_percentage ?? 0;

  const kpiCards: KpiCardProps[] = [
    {
      title: "Pacientes activos",
      value: dashboardLoading ? "..." : String(patientTotal),
      subtitle: patientTotal === 0 ? "Registra tu primer paciente" : `+${newPatients} este mes`,
      icon: Users,
      iconColor: "text-primary-600",
      iconBg: "bg-primary-50 dark:bg-primary-900/30",
      trend: patientGrowth > 0 ? `${patientGrowth}% vs mes anterior` : undefined,
    },
    {
      title: role === "doctor" ? "Mis citas hoy" : "Citas hoy (clínica)",
      value: dashboardLoading ? "..." : String(todayAppointments),
      subtitle: todayAppointments === 0 ? "Sin citas programadas" : `${todayAppointments} programadas`,
      icon: CalendarDays,
      iconColor: "text-secondary-600",
      iconBg: "bg-secondary-50 dark:bg-secondary-900/30",
    },
    {
      title: "Tratamientos pendientes",
      value: dashboardLoading ? "..." : String(Math.max(0, pendingTreatments)),
      subtitle: pendingTreatments === 0 ? "Todo al día" : `${dashboard?.appointments.completed ?? 0} completados`,
      icon: ClipboardList,
      iconColor: "text-accent-600",
      iconBg: "bg-accent-50 dark:bg-accent-900/30",
    },
    {
      title: "Ingresos del mes",
      value: dashboardLoading ? "..." : formatCurrency(monthRevenue),
      subtitle: monthRevenue === 0 ? "Sin ingresos registrados" : undefined,
      icon: DollarSign,
      iconColor: "text-success-600",
      iconBg: "bg-success-50 dark:bg-success-700/20",
      trend: revenueGrowth > 0 ? `${revenueGrowth}% vs mes anterior` : undefined,
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* ── Welcome header ── */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          Bienvenido, {firstName}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {welcomeSubtitle}
        </p>
      </div>

      {/* ── KPI cards ── */}
      <section aria-label="Indicadores clave">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {kpiCards.map((kpi) => (
            <KpiCard key={kpi.title} {...kpi} />
          ))}
        </div>
      </section>

      {/* ── Referral widget (doctor only) ── */}
      {role === "doctor" && (
        <section aria-label="Referencias pendientes">
          <ReferralWidget />
        </section>
      )}

      {/* ── Quick actions ── */}
      <section aria-label="Acciones rápidas">
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
          Acciones rápidas
        </h2>
        <div className="flex flex-wrap gap-3">
          {QUICK_ACTIONS.map((action) => {
            const ActionIcon = action.icon;
            return (
              <Button
                key={action.href}
                asChild
                variant={action.variant === "primary" ? "default" : "outline"}
              >
                <Link href={action.href}>
                  <ActionIcon className="h-4 w-4" aria-hidden="true" />
                  {action.label}
                </Link>
              </Button>
            );
          })}
        </div>
      </section>

      {/* ── Empty state / Getting started ── */}
      {!dashboardLoading && patientTotal === 0 && (
        <section aria-label="Primeros pasos">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
            Primeros pasos
          </h2>
          <EmptyState />
        </section>
      )}
    </div>
  );
}
