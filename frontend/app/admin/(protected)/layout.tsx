"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdminShell } from "@/components/layout/admin-shell";
import { useAdminAuthStore, clearAdminToken } from "@/lib/hooks/use-admin-auth";

// ─── Full-page Admin Skeleton ──────────────────────────────────────────────────

/**
 * Shown during brief auth-check transitions (e.g. TOTP step loading).
 * Mirrors the admin layout structure with indigo accent instead of teal.
 */
function AdminLoadingSkeleton() {
  return (
    <div
      className="flex h-screen overflow-hidden bg-[hsl(var(--background))] animate-pulse"
      aria-label="Cargando panel de administración..."
      aria-busy="true"
    >
      {/* Sidebar skeleton */}
      <div className="hidden md:flex flex-col w-64 border-r border-[hsl(var(--border))] bg-[hsl(var(--background))] shrink-0">
        {/* Logo area */}
        <div className="h-16 border-b border-[hsl(var(--border))] px-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-indigo-200 dark:bg-indigo-900/40" />
          <div className="h-5 w-32 rounded bg-slate-200 dark:bg-zinc-700" />
        </div>
        {/* Nav items */}
        <div className="p-3 space-y-2 flex-1">
          {[1, 2, 3, 4, 5, 6].map((i) => (
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
            <div className="h-8 w-28 rounded bg-slate-200 dark:bg-zinc-700" />
            <div className="h-8 w-24 rounded bg-slate-200 dark:bg-zinc-700" />
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

// ─── Layout + Auth Guard ──────────────────────────────────────────────────────

/**
 * Admin route group layout.
 *
 * Auth strategy differs from the clinic dashboard:
 * - There is NO /auth/me endpoint for admins — the store starts empty on reload.
 * - On reload: store is empty → is_authenticated = false → redirect to /admin/login.
 * - On login: AdminLoginPage calls set_admin_auth → store is populated → this
 *   layout re-renders and shows AdminShell.
 * - On 401: the adminApiClient interceptor calls clear_admin_auth and redirects
 *   to /admin/login via window.location (handled outside React).
 *
 * This is intentional for the high-privilege superadmin role — no persistent
 * browser session across page reloads.
 */
export default function AdminLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { admin, is_authenticated, is_loading, clear_admin_auth } =
    useAdminAuthStore();

  // Redirect to login when the store is empty (page reload or expired session)
  useEffect(() => {
    if (!is_loading && !is_authenticated) {
      router.replace("/admin/login");
    }
  }, [is_loading, is_authenticated, router]);

  function handleSignOut() {
    clearAdminToken();
    clear_admin_auth();
    router.replace("/admin/login");
  }

  // Show skeleton during brief state transitions
  if (is_loading) {
    return <AdminLoadingSkeleton />;
  }

  // Unauthenticated — show nothing while useEffect redirect fires
  if (!is_authenticated || !admin) {
    return null;
  }

  return (
    <AdminShell adminName={admin.name} onSignOut={handleSignOut}>
      {children}
    </AdminShell>
  );
}
