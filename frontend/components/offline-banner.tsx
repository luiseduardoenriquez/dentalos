"use client";

import { useEffect, useRef, useState } from "react";
import { WifiOff, Wifi } from "lucide-react";
import { useOnlineStore } from "@/lib/stores/online-store";

/**
 * Amber banner shown when the device is offline.
 * Auto-dismisses with a green "Reconectado" flash when connectivity returns.
 * Modeled on VoiceRecoveryBanner pattern.
 */
export function OfflineBanner() {
  const is_online = useOnlineStore((s) => s.is_online);
  const went_offline_at = useOnlineStore((s) => s.went_offline_at);
  const [show_reconnected, set_show_reconnected] = useState(false);
  const was_offline = useRef(false);

  // Track transitions: offline → online triggers reconnected flash
  useEffect(() => {
    if (!is_online) {
      was_offline.current = true;
      set_show_reconnected(false);
      return;
    }

    if (was_offline.current && is_online) {
      set_show_reconnected(true);
      was_offline.current = false;
      const timer = setTimeout(() => set_show_reconnected(false), 3_000);
      return () => clearTimeout(timer);
    }
  }, [is_online]);

  // Reconnected flash (green)
  if (show_reconnected) {
    return (
      <div
        className="border-b border-emerald-300 bg-emerald-50 px-4 py-2.5 dark:border-emerald-700 dark:bg-emerald-950/30 animate-in fade-in slide-in-from-top-1 duration-300"
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center gap-2">
          <Wifi
            className="h-4 w-4 text-emerald-600 dark:text-emerald-400"
            aria-hidden="true"
          />
          <p className="text-sm font-medium text-emerald-800 dark:text-emerald-200">
            Reconectado
          </p>
        </div>
      </div>
    );
  }

  // Offline banner (amber)
  if (!is_online) {
    const offlineDuration = went_offline_at
      ? formatDuration(Date.now() - went_offline_at)
      : null;

    return (
      <div
        className="border-b border-amber-300 bg-amber-50 px-4 py-2.5 dark:border-amber-700 dark:bg-amber-950/30"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center gap-2">
          <WifiOff
            className="h-4 w-4 text-amber-600 dark:text-amber-400"
            aria-hidden="true"
          />
          <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
            Sin conexion a internet — Los cambios se guardaran localmente
          </p>
          {offlineDuration && (
            <span className="text-xs text-amber-600 dark:text-amber-400">
              ({offlineDuration})
            </span>
          )}
        </div>
      </div>
    );
  }

  return null;
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}min`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}min`;
}
