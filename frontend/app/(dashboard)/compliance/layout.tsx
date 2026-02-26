"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/compliance", label: "Estado RDA", exact: true },
  { href: "/compliance/rips", label: "RIPS" },
  { href: "/compliance/e-invoices", label: "Facturación Electrónica" },
];

export default function ComplianceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Cumplimiento</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Estado de cumplimiento normativo — Resolución 1888, RIPS, DIAN
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
                  : "border-transparent text-[hsl(var(--muted-foreground))] hover:text-foreground hover:border-[hsl(var(--border))]"
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
