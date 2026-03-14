"use client";

import { create } from "zustand";

// ─── Types ────────────────────────────────────────────────────────────────────

export type SyncStatus = "idle" | "syncing" | "synced" | "error" | "offline";

interface SyncState {
  status: SyncStatus;
  pending_count: number;
  last_synced_at: number | null;
  error_message: string | null;

  set_status: (status: SyncStatus) => void;
  set_pending_count: (count: number) => void;
  set_last_synced: (timestamp: number) => void;
  set_error: (message: string | null) => void;
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useSyncStore = create<SyncState>((set) => ({
  status: "idle",
  pending_count: 0,
  last_synced_at: null,
  error_message: null,

  set_status: (status) => set((state) => ({ status, error_message: status === "error" ? state.error_message : null })),
  set_pending_count: (pending_count) => set({ pending_count }),
  set_last_synced: (timestamp) => set({ last_synced_at: timestamp, status: "synced" }),
  set_error: (error_message) => set({ error_message, status: error_message ? "error" : "idle" }),
}));
