"use client";

import { create } from "zustand";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ConnectionEffectiveType = "4g" | "3g" | "2g" | "slow-2g" | "unknown";

interface OnlineState {
  /** Whether the device has real internet connectivity (not just WiFi) */
  is_online: boolean;
  /** Timestamp when the device went offline (null if online) */
  went_offline_at: number | null;
  /** Network effective type from Network Information API */
  effective_type: ConnectionEffectiveType;
  /** Whether Save-Data header is active */
  is_save_data: boolean;

  set_online: (online: boolean) => void;
  set_connection_info: (effective_type: ConnectionEffectiveType, is_save_data: boolean) => void;
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useOnlineStore = create<OnlineState>((set) => ({
  is_online: typeof navigator !== "undefined" ? navigator.onLine : true,
  went_offline_at: null,
  effective_type: "unknown",
  is_save_data: false,

  set_online: (online: boolean) =>
    set((state) => ({
      is_online: online,
      went_offline_at: online ? null : (state.went_offline_at ?? Date.now()),
    })),

  set_connection_info: (effective_type: ConnectionEffectiveType, is_save_data: boolean) =>
    set({ effective_type, is_save_data }),
}));
