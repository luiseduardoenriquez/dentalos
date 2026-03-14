"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Agenda Sub-navigation Tabs ─────────────────────────────────────────────

const AGENDA_TABS = [
  { href: "/agenda", label: "Calendario", exact: true },
  { href: "/agenda/today", label: "Hoy" },
];

// ─── Layout ──────────────────────────────────────────────────────────────────

export default function AgendaLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Section header + tabs */}
      <div className="flex items-center gap-2 px-6 pt-6">
        <CalendarDays className="h-5 w-5 text-primary-600" />
        <h1 className="text-lg font-semibold text-foreground">Agenda</h1>
      </div>

      <nav className="flex gap-1 border-b border-[hsl(var(--border))] px-6">
        {AGENDA_TABS.map((tab) => {
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
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
