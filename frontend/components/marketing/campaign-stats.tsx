"use client";

import * as React from "react";
import { Send, Eye, MousePointerClick, AlertTriangle, UserMinus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CampaignStatsData {
  total_sent: number;
  total_opened: number;
  total_clicked: number;
  total_bounced: number;
  total_unsubscribed: number;
}

interface CampaignStatsProps {
  stats: CampaignStatsData;
}

// ─── CampaignStats ────────────────────────────────────────────────────────────

export function CampaignStats({ stats }: CampaignStatsProps) {
  const totalSent = stats.total_sent ?? 0;
  const totalOpened = stats.total_opened ?? 0;
  const totalClicked = stats.total_clicked ?? 0;
  const totalBounced = stats.total_bounced ?? 0;
  const totalUnsubscribed = stats.total_unsubscribed ?? 0;

  const openRate =
    totalSent > 0
      ? (totalOpened / totalSent) * 100
      : 0;

  const clickRate =
    totalSent > 0
      ? (totalClicked / totalSent) * 100
      : 0;

  const bounceRate =
    totalSent > 0
      ? (totalBounced / totalSent) * 100
      : 0;

  const unsubRate =
    totalSent > 0
      ? (totalUnsubscribed / totalSent) * 100
      : 0;

  const statCards: StatCardConfig[] = [
    {
      label: "Enviados",
      value: totalSent.toLocaleString("es-CO"),
      icon: Send,
      iconClass: "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30",
      rate: null,
      progressColor: "bg-blue-500",
    },
    {
      label: "Abiertos",
      value: totalOpened.toLocaleString("es-CO"),
      icon: Eye,
      iconClass: "text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/30",
      rate: openRate,
      progressColor: "bg-primary-500",
    },
    {
      label: "Clics",
      value: totalClicked.toLocaleString("es-CO"),
      icon: MousePointerClick,
      iconClass: "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30",
      rate: clickRate,
      progressColor: "bg-green-500",
    },
    {
      label: "Rebotados",
      value: totalBounced.toLocaleString("es-CO"),
      icon: AlertTriangle,
      iconClass: "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30",
      rate: bounceRate,
      progressColor: "bg-orange-500",
    },
    {
      label: "Desuscritos",
      value: totalUnsubscribed.toLocaleString("es-CO"),
      icon: UserMinus,
      iconClass: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30",
      rate: unsubRate,
      progressColor: "bg-red-500",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {statCards.map((card) => (
        <StatCard key={card.label} config={card} />
      ))}
    </div>
  );
}

// ─── StatCard ─────────────────────────────────────────────────────────────────

interface StatCardConfig {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  iconClass: string;
  rate: number | null;
  progressColor: string;
}

function StatCard({ config }: { config: StatCardConfig }) {
  const Icon = config.icon;
  const ratePercent = config.rate !== null ? Math.min(config.rate, 100) : 0;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] p-4">
      {/* Icon + label */}
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-md",
            config.iconClass,
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
        <span className="text-xs font-medium text-[hsl(var(--muted-foreground))]">
          {config.label}
        </span>
      </div>

      {/* Value */}
      <div>
        <p className="text-2xl font-bold tabular-nums">{config.value}</p>
        {config.rate !== null && (
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-0.5">
            {config.rate.toFixed(1)}%
          </p>
        )}
      </div>

      {/* Progress bar */}
      {config.rate !== null && (
        <div className="space-y-1">
          <div className="h-1.5 w-full rounded-full bg-[hsl(var(--muted))]">
            <div
              className={cn("h-1.5 rounded-full transition-all", config.progressColor)}
              style={{ width: `${ratePercent}%` }}
              role="progressbar"
              aria-valuenow={ratePercent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${config.label}: ${config.rate.toFixed(1)}%`}
            />
          </div>
        </div>
      )}
    </div>
  );
}
