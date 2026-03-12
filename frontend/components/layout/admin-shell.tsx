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
import { Bell, LogOut, Menu, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { AdminSidebar } from "@/components/layout/admin-sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getInitials } from "@/lib/utils";
import {
  useAdminNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
} from "@/lib/hooks/use-admin";

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
  const [notifOpen, setNotifOpen] = React.useState(false);
  const { data: notifData } = useAdminNotifications({ pageSize: 10 });
  const { mutate: markRead } = useMarkNotificationRead();
  const { mutate: markAllRead } = useMarkAllNotificationsRead();
  const unreadCount = notifData?.unread_count ?? 0;

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

      {/* Right: admin name + notification bell + sign-out */}
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

        {/* Notification bell */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setNotifOpen((prev) => !prev)}
            className={cn(
              "relative flex h-9 w-9 items-center justify-center rounded-md",
              "text-[hsl(var(--muted-foreground))] hover:text-foreground hover:bg-[hsl(var(--muted))]",
              "transition-colors duration-150",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
            )}
            aria-label={`Notificaciones${unreadCount > 0 ? ` (${unreadCount} sin leer)` : ""}`}
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>

          {/* Dropdown */}
          {notifOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setNotifOpen(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 top-full mt-2 z-50 w-80 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] shadow-lg">
                <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-4 py-3">
                  <span className="text-sm font-semibold text-foreground">
                    Notificaciones
                  </span>
                  {unreadCount > 0 && (
                    <button
                      type="button"
                      onClick={() => markAllRead()}
                      className="text-xs text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 font-medium"
                    >
                      Marcar todas como leidas
                    </button>
                  )}
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {!notifData?.items || notifData.items.length === 0 ? (
                    <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                      No hay notificaciones
                    </div>
                  ) : (
                    notifData.items.map((notif) => (
                      <button
                        key={notif.id}
                        type="button"
                        onClick={() => {
                          if (!notif.is_read) markRead(notif.id);
                          setNotifOpen(false);
                        }}
                        className={cn(
                          "w-full text-left px-4 py-3 border-b border-[hsl(var(--border))] last:border-b-0",
                          "hover:bg-[hsl(var(--muted))] transition-colors",
                          !notif.is_read && "bg-indigo-50/50 dark:bg-indigo-900/10",
                        )}
                      >
                        <div className="flex items-start gap-2">
                          {!notif.is_read && (
                            <span className="mt-1.5 h-2 w-2 rounded-full bg-indigo-500 shrink-0" />
                          )}
                          <div className={cn("min-w-0", notif.is_read && "ml-4")}>
                            <p className="text-sm font-medium text-foreground truncate">
                              {notif.title}
                            </p>
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                              {notif.message}
                            </p>
                            <p className="text-[10px] text-muted-foreground mt-1">
                              {new Date(notif.created_at).toLocaleDateString(
                                "es-CO",
                                {
                                  day: "numeric",
                                  month: "short",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                },
                              )}
                            </p>
                          </div>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
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
