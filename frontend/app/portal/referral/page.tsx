"use client";

import { ReferralShareCard } from "@/components/portal/ReferralShareCard";
import { Gift } from "lucide-react";
import Link from "next/link";

// ─── Page ─────────────────────────────────────────────────────────────────────

/**
 * /portal/referral
 *
 * Patient portal referral page.
 * Shows the patient's unique referral code and sharing options.
 */
export default function PortalReferralPage() {
  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-[hsl(var(--foreground))] flex items-center gap-2">
          <Gift className="h-5 w-5 text-teal-600" />
          Programa de referidos
        </h1>
        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
          Invita a tus amigos y familiares. Ambos reciben un beneficio en la
          primera cita.
        </p>
      </div>

      {/* Share card */}
      <ReferralShareCard />

      {/* Link to rewards */}
      <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-5 py-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-[hsl(var(--foreground))]">
            Mis recompensas
          </p>
          <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
            Consulta el historial de beneficios que has ganado.
          </p>
        </div>
        <Link
          href="/portal/referral/rewards"
          className="inline-flex items-center gap-1.5 text-sm text-teal-600 hover:text-teal-700 font-medium hover:underline transition-colors"
        >
          Ver recompensas
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </Link>
      </div>

      {/* How it works */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
          ¿Cómo funciona?
        </h2>
        <ol className="space-y-3">
          {[
            {
              step: "1",
              title: "Comparte tu código",
              desc: "Envía tu código o enlace por WhatsApp, mensaje de texto o muéstrales el QR.",
            },
            {
              step: "2",
              title: "Tu amigo agenda una cita",
              desc: "Cuando tu amigo registre tu código al pedir su primera cita, el referido queda activo.",
            },
            {
              step: "3",
              title: "Ambos reciben su beneficio",
              desc: "Al completarse la cita, tu amigo y tú reciben el beneficio acordado automáticamente.",
            },
          ].map((item) => (
            <li
              key={item.step}
              className="flex items-start gap-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] px-5 py-4"
            >
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-teal-600 text-white text-xs font-bold flex items-center justify-center">
                {item.step}
              </div>
              <div>
                <p className="text-sm font-medium text-[hsl(var(--foreground))]">
                  {item.title}
                </p>
                <p className="mt-0.5 text-xs text-[hsl(var(--muted-foreground))]">
                  {item.desc}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
