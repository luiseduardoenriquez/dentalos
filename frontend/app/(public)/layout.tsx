import type { ReactNode } from "react";
import type { Metadata } from "next";
import { Stethoscope } from "lucide-react";

export const metadata: Metadata = {
  title: {
    default: "DentalOS",
    template: "%s | DentalOS",
  },
  description: "Software dental para clínicas en Latinoamérica",
};

// ─── Logo ─────────────────────────────────────────────────────────────────────

function PublicLogo() {
  return (
    <div className="flex items-center justify-center gap-2.5 mb-8">
      <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary-600 shadow-md">
        <Stethoscope className="w-5 h-5 text-white" aria-hidden="true" />
      </div>
      <span className="text-2xl font-bold tracking-tight text-primary-600 select-none">
        DentalOS
      </span>
    </div>
  );
}

// ─── Layout ───────────────────────────────────────────────────────────────────

/**
 * Public auth layout — used for login, register, forgot-password, etc.
 *
 * Centers content vertically and horizontally on a soft gradient background.
 * Renders the DentalOS logo above the card for all public pages.
 * Server component — no "use client" needed.
 */
export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12 bg-gradient-to-br from-primary-50 via-white to-secondary-50 dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-950">
      {/* Subtle dot pattern overlay */}
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.03] dark:opacity-[0.05]"
        style={{
          backgroundImage:
            "radial-gradient(circle, #2563eb 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
        aria-hidden="true"
      />

      <div className="relative z-10 w-full max-w-md">
        <PublicLogo />
        {children}
      </div>

      {/* Footer tagline */}
      <p className="relative z-10 mt-8 text-xs text-center text-slate-400 dark:text-zinc-600 select-none">
        &copy; {new Date().getFullYear()} DentalOS &mdash; Hecho para LATAM
      </p>
    </div>
  );
}
