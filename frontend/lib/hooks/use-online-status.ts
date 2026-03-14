"use client";

import { useEffect, useRef } from "react";
import { useOnlineStore, type ConnectionEffectiveType } from "@/lib/stores/online-store";
import { getApiBaseUrl } from "@/lib/api-base-url";

// ─── Constants ────────────────────────────────────────────────────────────────

const HEALTH_CHECK_URL = `${getApiBaseUrl()}/api/v1/health`;
const HEALTH_CHECK_TIMEOUT = 3_000;
const HEALTH_CHECK_INTERVAL_ONLINE = 30_000; // 30s when online
const HEALTH_CHECK_INTERVAL_OFFLINE = 5_000; // 5s when offline (faster recovery detection)

// ─── Network Information API types ────────────────────────────────────────────

interface NetworkInformation extends EventTarget {
  effectiveType: "4g" | "3g" | "2g" | "slow-2g";
  saveData: boolean;
  addEventListener(type: "change", listener: () => void): void;
  removeEventListener(type: "change", listener: () => void): void;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Monitors real internet connectivity — not just `navigator.onLine` (which only
 * reports link-layer status). Pings `/api/v1/health` with a 3s timeout to detect
 * "WiFi without internet" scenarios common in clinics.
 *
 * Updates the global `useOnlineStore` Zustand store.
 */
export function useOnlineStatus() {
  const { is_online, set_online, set_connection_info } = useOnlineStore();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Real connectivity check via health endpoint
  useEffect(() => {
    let cancelled = false;

    async function checkConnectivity() {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT);
        await fetch(HEALTH_CHECK_URL, {
          method: "HEAD",
          cache: "no-store",
          signal: controller.signal,
        });
        clearTimeout(timeout);
        if (!cancelled) set_online(true);
      } catch {
        if (!cancelled) set_online(false);
      }
    }

    // Initial check
    checkConnectivity();

    // Periodic check — faster when offline for quicker recovery detection
    function startInterval() {
      if (intervalRef.current) clearInterval(intervalRef.current);
      const interval = useOnlineStore.getState().is_online
        ? HEALTH_CHECK_INTERVAL_ONLINE
        : HEALTH_CHECK_INTERVAL_OFFLINE;
      intervalRef.current = setInterval(checkConnectivity, interval);
    }

    startInterval();

    // Re-evaluate interval when online status changes
    const unsubscribe = useOnlineStore.subscribe((state, prevState) => {
      if (state.is_online !== prevState.is_online) {
        startInterval();
      }
    });

    return () => {
      cancelled = true;
      unsubscribe();
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Browser online/offline events as fast signal (then health check confirms)
  useEffect(() => {
    function handleOnline() {
      // Optimistic, but health check will confirm
      set_online(true);
    }

    function handleOffline() {
      set_online(false);
    }

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [set_online]);

  // Network Information API (connection type, save-data)
  useEffect(() => {
    const nav = navigator as Navigator & { connection?: NetworkInformation };
    const connection = nav.connection;
    if (!connection) return;

    function updateConnectionInfo() {
      const conn = (navigator as Navigator & { connection?: NetworkInformation }).connection;
      if (conn) {
        set_connection_info(
          conn.effectiveType as ConnectionEffectiveType,
          conn.saveData ?? false,
        );
      }
    }

    updateConnectionInfo();
    connection.addEventListener("change", updateConnectionInfo);
    return () => connection.removeEventListener("change", updateConnectionInfo);
  }, [set_connection_info]);

  return { is_online };
}
