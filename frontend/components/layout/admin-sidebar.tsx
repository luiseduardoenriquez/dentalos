"use client";

/**
 * Admin panel sidebar navigation.
 *
 * Differences from Sidebar (clinic):
 * - Uses indigo accent color instead of teal/primary.
 * - No role filtering — all items are visible to all superadmins.
 * - No collapse/expand — always full-width (admin panel is desktop-only).
 * - "DentalOS Admin" branding instead of "DentalOS".
 * - No disabled/upcoming items.
 */

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Building2,
  BarChart3,
  CreditCard,
  Flag,
  Activity,
  ShieldCheck,
  Shield,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AdminNavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** When true, active state uses exact pathname match instead of startsWith. */
  exact?: boolean;
}

export interface AdminSidebarProps {
  /** Mobile overlay: whether the sidebar is visible on small screens. */
  mobileOpen: boolean;
  /** Called to close mobile overlay. */
  onMobileClose: () => void;
  className?: string;
}

// ─── Navigation config ────────────────────────────────────────────────────────

const ADMIN_NAV: AdminNavItem[] = [
  {
    href: "/admin/dashboard",
    label: "Panel",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    href: "/admin/tenants",
    label: "Clínicas",
    icon: Building2,
  },
  {
    href: "/admin/analytics",
    label: "Analíticas",
    icon: BarChart3,
  },
  {
    href: "/admin/plans",
    label: "Planes",
    icon: CreditCard,
  },
  {
    href: "/admin/feature-flags",
    label: "Feature Flags",
    icon: Flag,
  },
  {
    href: "/admin/health",
    label: "Salud del Sistema",
    icon: Activity,
  },
  {
    href: "/admin/security",
    label: "Seguridad",
    icon: Shield,
  },
];

// ─── NavLink ──────────────────────────────────────────────────────────────────

interface AdminNavLinkProps {
  item: AdminNavItem;
  pathname: string;
}

function AdminNavLink({ item, pathname }: AdminNavLinkProps) {
  const isActive = item.exact
    ? pathname === item.href
    : pathname === item.href || pathname.startsWith(item.href + "/");

  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2.5",
        "text-sm font-medium transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
        isActive
          ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
          : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] hover:text-foreground",
      )}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon
        className={cn(
          "h-4 w-4 shrink-0",
          isActive
            ? "text-indigo-600 dark:text-indigo-400"
            : "opacity-70",
        )}
      />
      <span>{item.label}</span>
    </Link>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function SidebarContent({
  pathname,
  onMobileClose,
  isMobile = false,
}: {
  pathname: string;
  onMobileClose: () => void;
  isMobile?: boolean;
}) {
  return (
    <aside
      className={cn(
        "flex flex-col h-full w-64 border-r border-[hsl(var(--border))]",
        "bg-[hsl(var(--background))] dark:bg-[hsl(var(--card))]",
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b border-[hsl(var(--border))] px-4 shrink-0">
        <Link
          href="/admin/dashboard"
          className="flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-md"
        >
          {/* Indigo icon instead of teal */}
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-600 shrink-0">
            <ShieldCheck className="h-4 w-4 text-white" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-bold text-sm tracking-tight text-foreground">
              Dental<span className="text-indigo-600">OS</span>
            </span>
            <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-medium uppercase tracking-widest">
              Admin
            </span>
          </div>
        </Link>

        {/* Mobile close button */}
        {isMobile && (
          <button
            type="button"
            onClick={onMobileClose}
            className="p-1 rounded-md text-[hsl(var(--muted-foreground))] hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            aria-label="Cerrar menú"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-1" aria-label="Navegación de administración">
        {ADMIN_NAV.map((item) => (
          <AdminNavLink key={item.href} item={item} pathname={pathname} />
        ))}
      </nav>

      {/* Footer badge */}
      <div className="shrink-0 border-t border-[hsl(var(--border))] p-3">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-indigo-50 dark:bg-indigo-900/20">
          <ShieldCheck className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
          <span className="text-xs text-indigo-700 dark:text-indigo-300 font-medium">
            Panel de Superadmin
          </span>
        </div>
      </div>
    </aside>
  );
}

export function AdminSidebar({
  mobileOpen,
  onMobileClose,
  className,
}: AdminSidebarProps) {
  const pathname = usePathname();

  return (
    <div className={className}>
      {/* Desktop sidebar — always visible */}
      <div className="hidden md:flex h-full">
        <SidebarContent pathname={pathname} onMobileClose={onMobileClose} />
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={onMobileClose}
            aria-hidden="true"
          />
          {/* Drawer */}
          <div className="relative flex h-full">
            <SidebarContent
              pathname={pathname}
              onMobileClose={onMobileClose}
              isMobile
            />
          </div>
        </div>
      )}
    </div>
  );
}
