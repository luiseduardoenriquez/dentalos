"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import {
  Card,
  CardContent,
  CardDescription,
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
import { Pagination } from "@/components/pagination";
import {
  CreditCard,
  TrendingDown,
  TrendingUp,
  Users,
  DollarSign,
  ExternalLink,
} from "lucide-react";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface MembershipStats {
  active_count: number;
  monthly_revenue: number;
  churn_rate: number;
  new_this_month: number;
}

interface ActiveSubscription {
  id: string;
  patient_id: string;
  patient_name: string;
  plan_name: string;
  price_monthly: number;
  started_at: string;
  next_billing_date: string;
  status: string;
}

interface SubscriptionList {
  items: ActiveSubscription[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
}: {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  trend?: "up" | "down" | "neutral";
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-primary-600" />
          {title}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold tabular-nums">{value}</span>
          {trend === "up" && <TrendingUp className="h-4 w-4 text-green-500" />}
          {trend === "down" && <TrendingDown className="h-4 w-4 text-red-500" />}
        </div>
        {subtitle && (
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Status labels ────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  active: "Activa",
  cancelled: "Cancelada",
  past_due: "Vencida",
};

const STATUS_VARIANTS: Record<string, "success" | "secondary" | "destructive"> = {
  active: "success",
  cancelled: "secondary",
  past_due: "destructive",
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MembershipsDashboardPage() {
  const [page, setPage] = React.useState(1);

  const { data: stats, isLoading: isLoadingStats } = useQuery({
    queryKey: ["memberships", "stats"],
    queryFn: () => apiGet<MembershipStats>("/memberships/stats"),
    staleTime: 60_000,
  });

  const { data: subscriptions, isLoading: isLoadingSubs } = useQuery({
    queryKey: ["memberships", "subscriptions", page],
    queryFn: () =>
      apiGet<SubscriptionList>("/memberships/subscriptions", {
        page,
        page_size: 20,
      }),
    staleTime: 30_000,
  });

  const isLoading = isLoadingStats || isLoadingSubs;

  if (isLoading && !stats) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CreditCard className="h-5 w-5 text-primary-600" />
          <h1 className="text-lg font-semibold text-foreground">Membresías</h1>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/settings/memberships">Administrar planes</Link>
        </Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Miembros activos"
            value={stats.active_count.toLocaleString("es-CO")}
            icon={Users}
            subtitle={`+${stats.new_this_month} este mes`}
            trend="up"
          />
          <StatCard
            title="Ingresos mensuales"
            value={formatCurrency(stats.monthly_revenue)}
            icon={DollarSign}
            trend="up"
          />
          <StatCard
            title="Churn rate"
            value={`${stats.churn_rate.toFixed(1)}%`}
            icon={TrendingDown}
            subtitle="Últimos 30 días"
            trend={stats.churn_rate > 5 ? "down" : "neutral"}
          />
          <StatCard
            title="Nuevos este mes"
            value={stats.new_this_month.toLocaleString("es-CO")}
            icon={TrendingUp}
          />
        </div>
      )}

      {/* Subscriptions table */}
      <Card>
        <CardHeader>
          <CardTitle>Suscripciones activas</CardTitle>
          <CardDescription>
            Lista de todos los pacientes con membresía activa.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!subscriptions || subscriptions.items.length === 0 ? (
            <div className="text-center py-10">
              <CreditCard className="h-10 w-10 mx-auto text-[hsl(var(--muted-foreground))] opacity-40 mb-3" />
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No hay suscripciones activas todavía.
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Paciente</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead>Precio</TableHead>
                    <TableHead>Desde</TableHead>
                    <TableHead>Próx. cobro</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {subscriptions.items.map((sub) => (
                    <TableRow key={sub.id}>
                      <TableCell className="text-sm font-medium">
                        {sub.patient_name}
                      </TableCell>
                      <TableCell className="text-sm">{sub.plan_name}</TableCell>
                      <TableCell className="text-sm tabular-nums">
                        {formatCurrency(sub.price_monthly)}/mes
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {formatDate(sub.started_at)}
                      </TableCell>
                      <TableCell className="text-sm text-[hsl(var(--muted-foreground))]">
                        {formatDate(sub.next_billing_date)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={STATUS_VARIANTS[sub.status] ?? "secondary"}
                          className="text-xs"
                        >
                          {STATUS_LABELS[sub.status] ?? sub.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/patients/${sub.patient_id}/membership`}
                          className="text-[hsl(var(--muted-foreground))] hover:text-foreground"
                          title="Ver membresía"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {subscriptions.total > 20 && (
                <div className="mt-4">
                  <Pagination
                    page={page}
                    pageSize={20}
                    total={subscriptions.total}
                    onChange={setPage}
                  />
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
