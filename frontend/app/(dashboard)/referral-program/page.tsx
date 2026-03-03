"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Users, UserPlus, TrendingUp, Gift, Award } from "lucide-react";
import { formatCurrency, getInitials } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReferralStats {
  total_referrals: number;
  successful_referrals: number;
  conversion_rate: number;
  total_rewards_cents: number;
  active_referrers: number;
}

interface TopReferrer {
  patient_id: string;
  patient_name: string;
  referral_count: number;
  successful_count: number;
  rewards_earned_cents: number;
  conversion_rate: number;
}

interface ReferralDashboardData {
  stats: ReferralStats;
  top_referrers: TopReferrer[];
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  subtitle,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  subtitle?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-50 dark:bg-primary-900/30">
            <Icon className="h-5 w-5 text-primary-600" />
          </div>
          <div>
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">{label}</p>
            {subtitle && (
              <p className="text-xs text-primary-600 font-medium mt-0.5">{subtitle}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Top Referrers Table Columns ──────────────────────────────────────────────

const topReferrerColumns: ColumnDef<TopReferrer>[] = [
  {
    key: "patient_name",
    header: "Paciente referidor",
    cell: (row) => (
      <div className="flex items-center gap-3">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="text-xs">{getInitials(row.patient_name)}</AvatarFallback>
        </Avatar>
        <span className="font-medium text-sm">{row.patient_name}</span>
      </div>
    ),
  },
  {
    key: "referral_count",
    header: "Referidos",
    cell: (row) => <span className="text-sm font-medium">{row.referral_count}</span>,
  },
  {
    key: "successful_count",
    header: "Exitosos",
    cell: (row) => (
      <Badge variant="success" className="text-xs">
        {row.successful_count}
      </Badge>
    ),
  },
  {
    key: "conversion_rate",
    header: "Conversión",
    cell: (row) => (
      <span className="text-sm text-[hsl(var(--muted-foreground))]">
        {(row.conversion_rate * 100).toFixed(0)}%
      </span>
    ),
  },
  {
    key: "rewards_earned_cents",
    header: "Recompensas",
    cell: (row) => (
      <span className="text-sm font-semibold text-primary-600">
        {formatCurrency(row.rewards_earned_cents)}
      </span>
    ),
  },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ReferralProgramPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["referral_dashboard"],
    queryFn: () => apiGet<ReferralDashboardData>("/referral-program/dashboard"),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-4 w-96 mt-2" />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <div className="space-y-1">
                    <Skeleton className="h-6 w-16" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  const stats = data?.stats;
  const topReferrers = data?.top_referrers ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Programa de referidos
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Seguimiento de pacientes que refieren nuevos pacientes a la clínica.
        </p>
      </div>

      {/* Stats Grid */}
      {stats && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            icon={UserPlus}
            label="Total referidos"
            value={String(stats.total_referrals)}
          />
          <StatCard
            icon={TrendingUp}
            label="Tasa de conversión"
            value={`${(stats.conversion_rate * 100).toFixed(0)}%`}
            subtitle={`${stats.successful_referrals} exitosos`}
          />
          <StatCard
            icon={Gift}
            label="Recompensas otorgadas"
            value={formatCurrency(stats.total_rewards_cents)}
          />
          <StatCard
            icon={Users}
            label="Referidores activos"
            value={String(stats.active_referrers)}
          />
        </div>
      )}

      {/* Top Referrers Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Award className="h-4 w-4 text-primary-600" />
            Top referidores
          </CardTitle>
        </CardHeader>
        <CardContent>
          {topReferrers.length === 0 ? (
            <EmptyState
              icon={Users}
              title="Sin referidos todavía"
              description="Cuando los pacientes comiencen a referir, aparecerán aquí."
            />
          ) : (
            <DataTable<TopReferrer>
              columns={topReferrerColumns}
              data={topReferrers}
              rowKey="patient_id"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
