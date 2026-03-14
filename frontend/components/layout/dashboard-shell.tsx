"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Sidebar, type UserRole } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { NotificationDrawer } from "@/components/notifications/notification-drawer";
import { PatientSearchDialog } from "@/components/patients/patient-search-dialog";
import { GlobalVoiceFab } from "@/components/voice/global-voice-fab";
import { SyncStatusIndicator } from "@/components/sync-status-indicator";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DashboardShellProps {
  children: React.ReactNode;
  /** Current user's role — drives sidebar nav filtering */
  userRole: UserRole;
  /** Display name of the logged-in user */
  userName: string;
  /** Clinic display name shown in the header */
  clinicName: string;
  /** Optional avatar URL */
  userAvatarUrl?: string;
  /** Unread notification count */
  notificationCount?: number;
  /** Called on sign out action */
  onSignOut: () => void;
  /** Called when global search is triggered */
  onSearchClick?: () => void;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Main dashboard layout: sidebar (left) + header (top) + scrollable content area.
 *
 * Manages sidebar collapse state and mobile overlay state internally.
 * Responsive: sidebar collapses to overlay on mobile (< md breakpoint).
 */
export function DashboardShell({
  children,
  userRole,
  userName,
  clinicName,
  userAvatarUrl,
  notificationCount = 0,
  onSignOut,
  onSearchClick,
  className,
}: DashboardShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [notificationDrawerOpen, setNotificationDrawerOpen] = React.useState(false);
  const [searchOpen, setSearchOpen] = React.useState(false);

  // ─── ⌘K / Ctrl+K global shortcut ──────────────────────────────────────────
  React.useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  function handleToggleCollapse() {
    setSidebarCollapsed((prev) => !prev);
  }

  function handleMobileClose() {
    setMobileOpen(false);
  }

  function handleMenuToggle() {
    setMobileOpen((prev) => !prev);
  }

  return (
    <div className={cn("flex h-screen overflow-hidden bg-[hsl(var(--background))]", className)}>
      {/* Sidebar */}
      <Sidebar
        role={userRole}
        collapsed={sidebarCollapsed}
        onToggleCollapse={handleToggleCollapse}
        mobileOpen={mobileOpen}
        onMobileClose={handleMobileClose}
      />

      {/* Main column: header + content */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <Header
          clinicName={clinicName}
          userName={userName}
          userRole={userRole}
          userAvatarUrl={userAvatarUrl}
          notificationCount={notificationCount}
          onMenuToggle={handleMenuToggle}
          onSignOut={onSignOut}
          onSearchClick={onSearchClick ?? (() => setSearchOpen(true))}
          onNotificationClick={() => setNotificationDrawerOpen(true)}
          syncIndicator={<SyncStatusIndicator />}
        />

        {/* Scrollable content area */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 md:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </div>

      {/* Patient search dialog (⌘K) */}
      <PatientSearchDialog open={searchOpen} onOpenChange={setSearchOpen} />

      {/* Notification drawer */}
      <NotificationDrawer
        open={notificationDrawerOpen}
        onOpenChange={setNotificationDrawerOpen}
      />

      {/* Global voice FAB */}
      <GlobalVoiceFab />
    </div>
  );
}
