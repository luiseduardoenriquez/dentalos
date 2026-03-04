"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Receipt } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Billing Sub-navigation Tabs ────────────────────────────────────────────

const BILLING_TABS = [
  { href: "/billing", label: "Facturas", exact: true },
  { href: "/billing/cash-register", label: "Caja" },
  { href: "/billing/expenses", label: "Gastos" },
  { href: "/billing/eps-claims", label: "EPS" },
  { href: "/billing/commissions", label: "Comisiones" },
  { href: "/billing/tasks", label: "Tareas" },
];

// ─── Layout ──────────────────────────────────────────────────────────────────

export default function BillingLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <Receipt className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">Facturación</h1>
      </div>

      {/* Tab navigation */}
      <nav className="flex gap-1 border-b border-[hsl(var(--border))]">
        {BILLING_TABS.map((tab) => {
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

      {/* Page content */}
      {children}
    </div>
  );
}
