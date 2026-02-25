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
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/hooks/use-auth";
import { cn } from "@/lib/utils";

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

const KPI_CARDS: KpiCardProps[] = [
  {
    title: "Pacientes activos",
    value: "0",
    subtitle: "Registra tu primer paciente",
    icon: Users,
    iconColor: "text-primary-600",
    iconBg: "bg-primary-50 dark:bg-primary-900/30",
  },
  {
    title: "Citas hoy",
    value: "0",
    subtitle: "Sin citas programadas",
    icon: CalendarDays,
    iconColor: "text-secondary-600",
    iconBg: "bg-secondary-50 dark:bg-secondary-900/30",
  },
  {
    title: "Tratamientos pendientes",
    value: "0",
    subtitle: "Al día con los tratamientos",
    icon: ClipboardList,
    iconColor: "text-accent-600",
    iconBg: "bg-accent-50 dark:bg-accent-900/30",
  },
  {
    title: "Ingresos del mes",
    value: "$0",
    subtitle: "Acumulado este mes",
    icon: DollarSign,
    iconColor: "text-success-600",
    iconBg: "bg-success-50 dark:bg-success-700/20",
  },
];

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
    href: "/appointments/new",
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

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* ── Welcome header ── */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          Bienvenido, {firstName}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Panel de{" "}
          <span className="font-medium text-foreground">{tenant?.name}</span>
          {" "}— aquí tienes el resumen de hoy.
        </p>
      </div>

      {/* ── KPI cards ── */}
      <section aria-label="Indicadores clave">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {KPI_CARDS.map((kpi) => (
            <KpiCard key={kpi.title} {...kpi} />
          ))}
        </div>
      </section>

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
      <section aria-label="Primeros pasos">
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">
          Primeros pasos
        </h2>
        <EmptyState />
      </section>
    </div>
  );
}
