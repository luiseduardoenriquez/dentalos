"use client";

import { usePortalAuthStore } from "@/lib/stores/portal-auth-store";
import { usePortalMe } from "@/lib/hooks/use-portal";
import Link from "next/link";

export default function PortalDashboard() {
  const { patient } = usePortalAuthStore();
  const { data: profile } = usePortalMe();

  if (!patient) return null;

  const nextAppt = profile?.next_appointment;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Greeting */}
      <div className="bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-950/30 dark:to-primary-900/20 rounded-xl p-6">
        <h1 className="text-2xl font-bold text-[hsl(var(--foreground))]">
          Hola, {patient.first_name}
        </h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
          Bienvenido(a) a tu portal de paciente
        </p>
      </div>

      {/* Next Appointment */}
      {nextAppt ? (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-5">
          <h2 className="text-sm font-medium text-[hsl(var(--muted-foreground))] mb-3">
            Próxima cita
          </h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-[hsl(var(--foreground))]">
                {nextAppt.doctor_name}
              </p>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                {new Date(nextAppt.scheduled_at).toLocaleDateString("es-CO", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
              <span className="inline-block mt-1 px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700 dark:bg-green-950/30 dark:text-green-400">
                {nextAppt.status === "confirmed"
                  ? "Confirmada"
                  : nextAppt.status === "pending"
                    ? "Pendiente"
                    : nextAppt.status}
              </span>
            </div>
            <Link
              href="/portal/appointments"
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              Ver todas
            </Link>
          </div>
        </div>
      ) : (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-5 text-center">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            No tienes citas próximas
          </p>
          <Link
            href="/portal/appointments"
            className="inline-block mt-2 text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            Agendar una cita
          </Link>
        </div>
      )}

      {/* Summary Grid — 2x2 */}
      <div className="grid grid-cols-2 gap-4">
        <Link
          href="/portal/treatment-plans"
          className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4 hover:border-primary-300 dark:hover:border-primary-700 transition-colors"
        >
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Planes de tratamiento
          </p>
          <p className="text-lg font-bold text-[hsl(var(--foreground))] mt-1">
            Ver planes
          </p>
        </Link>

        <Link
          href="/portal/messages"
          className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4 hover:border-primary-300 dark:hover:border-primary-700 transition-colors"
        >
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Mensajes
          </p>
          <p className="text-lg font-bold text-[hsl(var(--foreground))] mt-1">
            Bandeja
          </p>
        </Link>

        <Link
          href="/portal/documents"
          className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4 hover:border-primary-300 dark:hover:border-primary-700 transition-colors"
        >
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Consentimientos pendientes
          </p>
          <p className="text-lg font-bold text-[hsl(var(--foreground))] mt-1">
            Mis docs
          </p>
        </Link>

        <Link
          href="/portal/invoices"
          className="bg-white dark:bg-zinc-900 rounded-xl border border-[hsl(var(--border))] p-4 hover:border-primary-300 dark:hover:border-primary-700 transition-colors"
        >
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Saldo pendiente
          </p>
          <p className="text-lg font-bold text-[hsl(var(--foreground))] mt-1">
            $
            {((profile?.outstanding_balance ?? 0) / 100).toLocaleString(
              "es-CO",
            )}
          </p>
        </Link>
      </div>

      {/* CTA */}
      <div className="text-center">
        <Link
          href="/portal/appointments"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
        >
          Agendar nueva cita
        </Link>
      </div>
    </div>
  );
}
