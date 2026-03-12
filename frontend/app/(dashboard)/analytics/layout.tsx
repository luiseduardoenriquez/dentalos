"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/analytics", label: "Resumen", exact: true },
  { href: "/analytics/patients", label: "Pacientes" },
  { href: "/analytics/appointments", label: "Citas" },
  { href: "/analytics/revenue", label: "Ingresos" },
  { href: "/analytics/profit-loss", label: "P&G" },
  { href: "/analytics/nps", label: "NPS" },
  { href: "/analytics/acceptance-rate", label: "Aceptación" },
  { href: "/analytics/compliance", label: "Cumplimiento" },
  { href: "/analytics/schedule-intelligence", label: "Inteligencia" },
];

export default function AnalyticsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analíticas</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Métricas y tendencias de la clínica — pacientes, citas e ingresos
        </p>
      </div>

      {/* Tab navigation */}
      <nav className="flex gap-1 border-b border-[hsl(var(--border))]">
        {TABS.map((tab) => {
          const isActive = tab.exact
            ? pathname === tab.href
            : pathname === tab.href || pathname.startsWith(tab.href + "/");

          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
                isActive
                  ? "border-primary-600 text-primary-700 dark:text-primary-300"
                  : "border-transparent text-[hsl(var(--muted-foreground))] hover:text-foreground hover:border-[hsl(var(--border))]",
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {children}
    </div>
  );
}
