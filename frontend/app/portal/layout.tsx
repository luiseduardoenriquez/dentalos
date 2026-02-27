"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { usePortalAuthStore } from "@/lib/stores/portal-auth-store";
import { usePortalMe } from "@/lib/hooks/use-portal";

// ─── Loading Skeleton ────────────────────────────────────────────────────────

function PortalLoadingSkeleton() {
  return (
    <div
      className="flex h-screen flex-col bg-[hsl(var(--background))] animate-pulse"
      aria-label="Cargando portal..."
      aria-busy="true"
    >
      <div className="h-16 border-b border-[hsl(var(--border))] px-4 flex items-center gap-3">
        <div className="w-8 h-8 rounded-md bg-primary-200 dark:bg-primary-900/40" />
        <div className="h-5 w-32 rounded bg-slate-200 dark:bg-zinc-700" />
      </div>
      <div className="flex-1 p-6 space-y-4">
        <div className="h-8 w-48 rounded bg-slate-200 dark:bg-zinc-700" />
        <div className="h-32 rounded-xl bg-slate-100 dark:bg-zinc-800" />
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 rounded-xl bg-slate-100 dark:bg-zinc-800" />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Portal Navigation ──────────────────────────────────────────────────────

const PORTAL_NAV_ITEMS = [
  { href: "/portal/dashboard", label: "Inicio", icon: "🏠" },
  { href: "/portal/appointments", label: "Mis citas", icon: "📅" },
  { href: "/portal/treatment-plans", label: "Plan de tratamiento", icon: "📋" },
  { href: "/portal/documents", label: "Documentos", icon: "📄" },
  { href: "/portal/messages", label: "Mensajes", icon: "💬" },
  { href: "/portal/invoices", label: "Pagos", icon: "💳" },
  { href: "/portal/odontogram", label: "Odontograma", icon: "🦷" },
];

function PortalNavbar({
  patientName,
  onSignOut,
}: {
  patientName: string;
  onSignOut: () => void;
}) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 h-16 border-b border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 rounded-md hover:bg-slate-100 dark:hover:bg-zinc-800"
            aria-label="Abrir menú"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-md bg-primary-600 flex items-center justify-center text-white text-sm font-bold">
              D
            </div>
            <span className="text-sm font-semibold text-[hsl(var(--foreground))] hidden sm:inline">
              DentalOS Portal
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-[hsl(var(--muted-foreground))]">
            {patientName}
          </span>
          <button
            onClick={onSignOut}
            className="text-sm text-red-500 hover:text-red-700 font-medium"
          >
            Salir
          </button>
        </div>
      </header>

      {/* Mobile side drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMenuOpen(false)}
          />
          <nav className="absolute left-0 top-0 h-full w-64 bg-[hsl(var(--background))] border-r border-[hsl(var(--border))] p-4 space-y-1">
            <div className="mb-4 pb-4 border-b border-[hsl(var(--border))]">
              <p className="text-sm font-semibold">{patientName}</p>
            </div>
            {PORTAL_NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
                  pathname === item.href
                    ? "bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300 font-medium"
                    : "text-[hsl(var(--muted-foreground))] hover:bg-slate-100 dark:hover:bg-zinc-800"
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
            <div className="pt-4 mt-4 border-t border-[hsl(var(--border))]">
              <button
                onClick={onSignOut}
                className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 w-full"
              >
                Cerrar sesión
              </button>
            </div>
          </nav>
        </div>
      )}

      {/* Desktop sidebar */}
      <nav className="hidden md:flex fixed left-0 top-16 h-[calc(100vh-4rem)] w-56 border-r border-[hsl(var(--border))] bg-[hsl(var(--background))] flex-col p-3 space-y-1">
        {PORTAL_NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
              pathname === item.href
                ? "bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300 font-medium"
                : "text-[hsl(var(--muted-foreground))] hover:bg-slate-100 dark:hover:bg-zinc-800"
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </>
  );
}

// ─── Portal Layout ──────────────────────────────────────────────────────────

export default function PortalLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { patient, is_loading, is_authenticated, clear_portal_auth } =
    usePortalAuthStore();

  // Login page doesn't need auth guard
  const isLoginPage = pathname === "/portal/login" || pathname === "/portal/register";

  // Hydrate portal auth on mount — skip on login/register to avoid
  // a 401 → refresh fail → redirect → reload loop.
  usePortalMe(!isLoginPage);

  async function handleSignOut() {
    try {
      const { portalApiPost } = await import("@/lib/portal-api-client");
      await portalApiPost("/portal/auth/logout", null);
    } catch {
      // Best-effort
    }
    clear_portal_auth();
    router.replace("/portal/login");
  }

  // Login page: no shell
  if (isLoginPage) {
    return <>{children}</>;
  }

  // Loading state
  if (is_loading || !is_authenticated || !patient) {
    return <PortalLoadingSkeleton />;
  }

  return (
    <div className="min-h-screen bg-[hsl(var(--background))]">
      <PortalNavbar
        patientName={`${patient.first_name} ${patient.last_name}`}
        onSignOut={handleSignOut}
      />
      <main className="md:ml-56 pt-0 p-4 md:p-6">{children}</main>
    </div>
  );
}
