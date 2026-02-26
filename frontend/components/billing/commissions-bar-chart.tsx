"use client";

import type { CommissionEntry } from "@/lib/hooks/use-commissions";
import { formatCurrency, cn } from "@/lib/utils";

interface CommissionsBarChartProps {
  commissions: CommissionEntry[];
}

export function CommissionsBarChart({ commissions }: CommissionsBarChartProps) {
  if (commissions.length === 0) return null;

  const maxRevenue = Math.max(...commissions.map((c) => c.total_revenue), 1);

  return (
    <div className="space-y-3">
      {commissions.map((entry) => {
        const revenuePercent = Math.round((entry.total_revenue / maxRevenue) * 100);
        const commissionPercent =
          entry.total_revenue > 0
            ? Math.round((entry.commission_amount / entry.total_revenue) * 100)
            : 0;

        return (
          <div key={entry.doctor.id} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium text-foreground truncate max-w-[200px]">
                  {entry.doctor.name}
                </span>
                {entry.doctor.specialty && (
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    {entry.doctor.specialty}
                  </span>
                )}
              </div>
              <span className="text-sm font-semibold tabular-nums text-foreground">
                {formatCurrency(entry.commission_amount, "COP")}
              </span>
            </div>
            <div className="relative h-6 w-full rounded-md bg-[hsl(var(--muted))] overflow-hidden">
              {/* Revenue bar */}
              <div
                className="absolute inset-y-0 left-0 rounded-md bg-primary-200 dark:bg-primary-900/40 transition-all duration-300"
                style={{ width: `${revenuePercent}%` }}
              />
              {/* Commission portion */}
              <div
                className="absolute inset-y-0 left-0 rounded-md bg-primary-500 dark:bg-primary-600 transition-all duration-300"
                style={{ width: `${Math.round((entry.commission_amount / maxRevenue) * 100)}%` }}
              />
              {/* Label inside bar */}
              <div className="relative flex items-center h-full px-2">
                <span className="text-[10px] font-medium text-white drop-shadow-sm">
                  {entry.commission_percentage}%
                </span>
              </div>
            </div>
            <div className="flex justify-between text-[10px] text-[hsl(var(--muted-foreground))]">
              <span>
                {entry.procedure_count} procedimiento{entry.procedure_count !== 1 ? "s" : ""}
              </span>
              <span>Ingreso: {formatCurrency(entry.total_revenue, "COP")}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
