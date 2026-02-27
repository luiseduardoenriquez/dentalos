"use client";

/**
 * Admin panel shell layout: sidebar (left) + simplified header (top) + scrollable content.
 *
 * Differences from DashboardShell (clinic):
 * - Uses AdminSidebar instead of Sidebar.
 * - Simplified header: admin name + sign-out button only.
 * - No notifications, no clinic name, no search.
 * - No NotificationDrawer.
 * - Sidebar never collapses (admin panel is a low-frequency, desktop-first tool).
 */

import * as React from "react";
import { LogOut, Menu, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { AdminSidebar } from "@/components/layout/admin-sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getInitials } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AdminShellProps {
  children: React.ReactNode;
  /** Display name of the logged-in superadmin */
  adminName: string;
  /** Called when the admin clicks "Cerrar sesión" */
  onSignOut: () => void;
  className?: string;
}

// ─── Admin Header ─────────────────────────────────────────────────────────────

interface AdminHeaderProps {
  adminName: string;
  onSignOut: () => void;
  onMenuToggle: () => void;
}

function AdminHeader({ adminName, onSignOut, onMenuToggle }: AdminHeaderProps) {
  const initials = getInitials(adminName);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 flex h-16 items-center gap-3 border-b border-[hsl(var(--border))]",
        "bg-[hsl(var(--background))]/95 backdrop-blur-sm px-4",
      )}
    >
      {/* Hamburger — mobile only */}
      <button
        type="button"
        onClick={onMenuToggle}
        className={cn(
          "flex md:hidden h-9 w-9 items-center justify-center rounded-md",
          "text-[hsl(var(--muted-foreground))] hover:text-foreground hover:bg-[hsl(var(--muted))]",
          "transition-colors duration-150 shrink-0",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
        )}
        aria-label="Abrir menú"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Admin panel label */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <ShieldCheck className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0 hidden md:block" />
        <h1 className="text-sm font-semibold text-foreground truncate">
          Panel de Administración
        </h1>
      </div>

      {/* Right: admin name + sign-out */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Admin identity */}
        <div className="hidden sm:flex items-center gap-2">
          <Avatar size="sm">
            <AvatarFallback className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="hidden md:flex flex-col leading-none">
            <span className="text-sm font-medium text-foreground max-w-[140px] truncate">
              {adminName}
            </span>
            <span className="text-xs text-[hsl(var(--muted-foreground))]">
              Superadmin
            </span>
          </div>
        </div>

        {/* Divider */}
        <div
          className="hidden sm:block h-6 w-px bg-[hsl(var(--border))]"
          aria-hidden="true"
        />

        {/* Sign-out button */}
        <button
          type="button"
          onClick={onSignOut}
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-1.5",
            "text-sm font-medium text-[hsl(var(--muted-foreground))]",
            "hover:bg-[hsl(var(--muted))] hover:text-foreground",
            "transition-colors duration-150",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
          )}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span className="hidden sm:inline">Cerrar sesión</span>
        </button>
      </div>
    </header>
  );
}

// ─── AdminShell ───────────────────────────────────────────────────────────────

export function AdminShell({
  children,
  adminName,
  onSignOut,
  className,
}: AdminShellProps) {
  const [mobileOpen, setMobileOpen] = React.useState(false);

  function handleMenuToggle() {
    setMobileOpen((prev) => !prev);
  }

  function handleMobileClose() {
    setMobileOpen(false);
  }

  return (
    <div
      className={cn(
        "flex h-screen overflow-hidden bg-[hsl(var(--background))]",
        className,
      )}
    >
      {/* Sidebar */}
      <AdminSidebar
        mobileOpen={mobileOpen}
        onMobileClose={handleMobileClose}
      />

      {/* Main column: header + scrollable content */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <AdminHeader
          adminName={adminName}
          onSignOut={onSignOut}
          onMenuToggle={handleMenuToggle}
        />

        {/* Scrollable content area */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 md:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
