"use client";

import { create } from "zustand";
import { setAccessToken, clearAccessToken } from "@/lib/auth";

// ─── Cookie names ────────────────────────────────────────────────────────────

const IMPERSONATION_COOKIE = "dentalos_impersonation";
const RETURN_PATH_COOKIE = "dentalos_impersonation_return";

// ─── Cookie helpers ──────────────────────────────────────────────────────────

function setCookie(name: string, value: string, maxAge = 3600): void {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; samesite=strict`;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${name}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

function deleteCookie(name: string): void {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; path=/; max-age=0`;
}

// ─── Store ───────────────────────────────────────────────────────────────────

interface ImpersonationState {
  /** True when the user is currently impersonating a clinic. */
  impersonating: boolean;

  /** Path to redirect back to when exiting impersonation. */
  return_path: string | null;

  /**
   * Enter impersonation mode.
   * Sets the access token, stores cookies for reload resilience,
   * and updates the store state.
   */
  enter: (token: string, returnPath: string) => void;

  /**
   * Exit impersonation mode.
   * Clears the impersonation token and cookies.
   * Returns the saved return path for redirect.
   */
  exit: () => string;

  /**
   * Rehydrate impersonation state from cookies on mount.
   * Call this in a useEffect to survive page reloads.
   */
  init: () => void;
}

export const useImpersonationStore = create<ImpersonationState>((set, get) => ({
  impersonating: false,
  return_path: null,

  enter: (token: string, returnPath: string) => {
    setAccessToken(token);
    setCookie(IMPERSONATION_COOKIE, "1", 3600);
    setCookie(RETURN_PATH_COOKIE, returnPath, 3600);
    set({ impersonating: true, return_path: returnPath });
  },

  exit: () => {
    const returnPath = get().return_path ?? "/admin/tenants";
    clearAccessToken();
    deleteCookie(IMPERSONATION_COOKIE);
    deleteCookie(RETURN_PATH_COOKIE);
    set({ impersonating: false, return_path: null });
    return returnPath;
  },

  init: () => {
    const flag = getCookie(IMPERSONATION_COOKIE);
    if (flag === "1") {
      const returnPath = getCookie(RETURN_PATH_COOKIE);
      set({
        impersonating: true,
        return_path: returnPath ?? "/admin/tenants",
      });
    }
  },
}));
