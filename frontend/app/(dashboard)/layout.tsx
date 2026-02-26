"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { useAuthStore } from "@/lib/hooks/use-auth";
import { clearAccessToken } from "@/lib/auth";
import { apiPost } from "@/lib/api-client";
import { useMe } from "@/lib/hooks/use-me";
import { useUnreadCount } from "@/lib/hooks/use-notifications";
import type { UserRole } from "@/components/layout/sidebar";

// ─── Full-page Skeleton ───────────────────────────────────────────────────────

function AuthLoadingSkeleton() {
  return (
    <div
      className="flex h-screen overflow-hidden bg-[hsl(var(--background))] animate-pulse"
      aria-label="Cargando panel..."
      aria-busy="true"
    >
      {/* Sidebar skeleton */}
      <div className="hidden md:flex flex-col w-64 border-r border-[hsl(var(--border))] bg-[hsl(var(--background))] shrink-0">
        {/* Logo area */}
        <div className="h-16 border-b border-[hsl(var(--border))] px-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-primary-200 dark:bg-primary-900/40" />
          <div className="h-5 w-24 rounded bg-slate-200 dark:bg-zinc-700" />
        </div>
        {/* Nav items */}
        <div className="p-3 space-y-2 flex-1">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-10 rounded-md bg-slate-100 dark:bg-zinc-800"
            />
          ))}
        </div>
      </div>

      {/* Main content skeleton */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="h-16 border-b border-[hsl(var(--border))] px-6 flex items-center justify-between">
          <div className="h-5 w-40 rounded bg-slate-200 dark:bg-zinc-700" />
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-slate-200 dark:bg-zinc-700" />
            <div className="h-5 w-24 rounded bg-slate-200 dark:bg-zinc-700" />
          </div>
        </div>
        {/* Content area */}
        <div className="flex-1 p-8 space-y-6">
          <div className="h-8 w-64 rounded bg-slate-200 dark:bg-zinc-700" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-28 rounded-xl bg-slate-100 dark:bg-zinc-800"
              />
            ))}
          </div>
          <div className="h-64 rounded-xl bg-slate-100 dark:bg-zinc-800" />
        </div>
      </div>
    </div>
  );
}

// ─── Auth Guard + Layout ──────────────────────────────────────────────────────

/**
 * Dashboard route group layout.
 *
 * Responsibilities:
 * 1. Calls GET /auth/me on every page load to rehydrate the access token
 *    and user/tenant context from the HttpOnly refresh cookie.
 * 2. Shows a full-page skeleton while the auth check is in flight.
 * 3. Redirects to /login on 401 (handled inside useMe via router.replace).
 * 4. Once authenticated, wraps all dashboard pages in DashboardShell.
 *
 * Note: DashboardShell receives user/tenant data from the Zustand store
 * (populated by useMe) so child pages do NOT need to thread these props down.
 */
export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { user, tenant, is_loading, is_authenticated } = useAuthStore();

  // Triggers GET /auth/me — hydrates store, redirects on 401
  useMe();

  // Real-time unread notification count (polls every 30s)
  const { data: unreadCount } = useUnreadCount();

  // Handle sign-out
  async function handleSignOut() {
    try {
      await apiPost("/auth/logout", null);
    } catch {
      // Best-effort — clear client state regardless of server response
    }
    clearAccessToken();
    useAuthStore.getState().clear_auth();
    router.replace("/login");
  }

  // While auth check is in flight or store is not yet hydrated, show skeleton
  if (is_loading || !is_authenticated || !user || !tenant) {
    return <AuthLoadingSkeleton />;
  }

  return (
    <DashboardShell
      userRole={user.role as UserRole}
      userName={user.name}
      clinicName={tenant.name}
      userAvatarUrl={user.avatar_url ?? undefined}
      notificationCount={unreadCount ?? 0}
      onSignOut={handleSignOut}
    >
      {children}
    </DashboardShell>
  );
}
