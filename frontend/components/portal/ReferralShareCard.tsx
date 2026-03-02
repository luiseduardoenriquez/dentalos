"use client";

import * as React from "react";
import { Copy, Check, MessageCircle, QrCode, Gift } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { portalApiGet } from "@/lib/portal-api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PortalReferral {
  referral_code: string;
  referral_url: string;
  uses_count: number;
  pending_rewards: number;
  reward_description: string | null;
}

// ─── QR Code display ──────────────────────────────────────────────────────────

/**
 * Renders a QR code via a free public API (Google Charts).
 * No third-party npm dependency needed.
 */
function QRCodeImage({ value, size = 160 }: { value: string; size?: number }) {
  const encoded = encodeURIComponent(value);
  const src = `https://api.qrserver.com/v1/create-qr-code/?data=${encoded}&size=${size}x${size}&bgcolor=ffffff&color=000000&margin=8`;

  return (
    <img
      src={src}
      alt="Código QR de referido"
      width={size}
      height={size}
      className="rounded-lg border border-[hsl(var(--border))] shadow-sm"
    />
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Patient portal card that lets the patient share their unique referral code.
 *
 * Features:
 * - Shows the referral code in large, copyable text.
 * - Copy-to-clipboard button with brief visual confirmation.
 * - "Compartir por WhatsApp" button.
 * - QR code display.
 * - Stats: how many friends referred, pending rewards.
 */
export function ReferralShareCard() {
  const [copied, setCopied] = React.useState(false);
  const [showQR, setShowQR] = React.useState(false);

  const { data: referral, isLoading, isError } = useQuery({
    queryKey: ["portal", "referral"],
    queryFn: () => portalApiGet<PortalReferral>("/portal/referral"),
    staleTime: 5 * 60_000,
  });

  async function handleCopy() {
    if (!referral?.referral_code) return;
    try {
      await navigator.clipboard.writeText(referral.referral_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select text
    }
  }

  function buildWhatsAppUrl() {
    if (!referral) return "#";
    const message = `¡Te invito a conocer mi clínica dental! Usa mi código *${referral.referral_code}* o ingresa aquí: ${referral.referral_url}`;
    return `https://wa.me/?text=${encodeURIComponent(message)}`;
  }

  // ─── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 space-y-4 animate-pulse">
        <div className="h-6 w-48 rounded bg-slate-200 dark:bg-zinc-700" />
        <div className="h-16 w-full rounded-xl bg-slate-100 dark:bg-zinc-800" />
        <div className="h-10 w-full rounded-lg bg-slate-100 dark:bg-zinc-800" />
      </div>
    );
  }

  // ─── Error ──────────────────────────────────────────────────────────────────
  if (isError || !referral) {
    return (
      <div className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
        No se pudo cargar tu código de referido. Intenta de nuevo más tarde.
      </div>
    );
  }

  // ─── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] shadow-sm overflow-hidden">
      {/* Header strip */}
      <div className="bg-teal-600 px-6 py-4">
        <div className="flex items-center gap-2">
          <Gift className="h-5 w-5 text-white" />
          <h2 className="text-base font-semibold text-white">
            Comparte y gana
          </h2>
        </div>
        <p className="mt-1 text-sm text-teal-100">
          Invita amigos a tu clínica y recibe beneficios.
          {referral.reward_description && (
            <span className="ml-1 font-medium text-white">
              {referral.reward_description}
            </span>
          )}
        </p>
      </div>

      <div className="p-6 space-y-5">
        {/* Referral code display */}
        <div className="flex flex-col items-center gap-3">
          <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
            Tu código de referido
          </p>
          <div className="flex items-center gap-3 bg-slate-50 dark:bg-zinc-900 rounded-xl px-5 py-3 border border-[hsl(var(--border))]">
            <span className="text-3xl font-bold font-mono tracking-widest text-[hsl(var(--foreground))]">
              {referral.referral_code}
            </span>
            <button
              onClick={handleCopy}
              aria-label="Copiar código"
              className="p-2 rounded-lg hover:bg-slate-200 dark:hover:bg-zinc-700 transition-colors text-[hsl(var(--muted-foreground))]"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </button>
          </div>
          {copied && (
            <p className="text-xs text-green-600 dark:text-green-400">
              Copiado al portapapeles
            </p>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <a
            href={buildWhatsAppUrl()}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-[#25D366] text-white px-4 py-2.5 text-sm font-medium hover:bg-[#1ebe5d] transition-colors"
          >
            <MessageCircle className="h-4 w-4" />
            Compartir por WhatsApp
          </a>

          <button
            onClick={() => setShowQR((v) => !v)}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--foreground))] px-4 py-2.5 text-sm font-medium hover:bg-slate-50 dark:hover:bg-zinc-800 transition-colors"
          >
            <QrCode className="h-4 w-4" />
            {showQR ? "Ocultar QR" : "Ver código QR"}
          </button>
        </div>

        {/* QR code */}
        {showQR && (
          <div className="flex justify-center">
            <QRCodeImage value={referral.referral_url} size={180} />
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 pt-1 border-t border-[hsl(var(--border))]">
          <StatCard
            label="Amigos referidos"
            value={referral.uses_count}
            color="teal"
          />
          <StatCard
            label="Recompensas pendientes"
            value={referral.pending_rewards}
            color={referral.pending_rewards > 0 ? "amber" : "slate"}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Stat card helper ─────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: "teal" | "amber" | "slate";
}) {
  const colorMap = {
    teal: "text-teal-600 dark:text-teal-400",
    amber: "text-amber-600 dark:text-amber-400",
    slate: "text-slate-500 dark:text-slate-400",
  };

  return (
    <div className="rounded-xl bg-slate-50 dark:bg-zinc-900 p-4 text-center">
      <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
      <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
        {label}
      </p>
    </div>
  );
}
