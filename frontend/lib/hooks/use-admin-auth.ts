"use client";

/**
 * Admin auth store and token helpers — completely separate from the clinic auth system.
 *
 * DESIGN NOTES:
 * - Admin sessions are 1 hour; no silent refresh. On expiry the user must log in again.
 * - The token lives in a module-level JS variable (same pattern as lib/auth.ts) so it
 *   is NOT accessible via localStorage/sessionStorage XSS vectors.
 * - A session indicator cookie `dentalos_admin_session` is set (NOT HttpOnly) so that
 *   Next.js proxy/middleware can gate /admin/* routes without reading the memory token.
 * - On page reload the store is empty and the admin must log in again — intentional for
 *   high-security admin operations.
 */

import { create } from "zustand";

// ─── Module-level token storage ────────────────────────────────────────────────
// Kept separate from lib/auth.ts — these two variables must NEVER be merged.

const ADMIN_SESSION_COOKIE = "dentalos_admin_session";

/** In-memory admin access token. Never written to localStorage. */
let adminAccessToken: string | null = null;

/**
 * Returns the current admin access token, or null if not authenticated.
 */
export function getAdminToken(): string | null {
  return adminAccessToken;
}

/**
 * Stores the admin access token in memory and sets the session indicator cookie.
 * The cookie is used by routing guards — it is NOT a security token.
 *
 * @param token - JWT access token string, or null to clear.
 */
export function setAdminToken(token: string | null): void {
  adminAccessToken = token;
  if (typeof document !== "undefined") {
    if (token) {
      // 1-hour cookie matching the server-side session TTL
      document.cookie = `${ADMIN_SESSION_COOKIE}=1; path=/admin; max-age=3600; samesite=strict`;
    }
  }
}

/**
 * Clears the in-memory admin token and removes the session cookie.
 * Called on logout or when the admin session expires (401 response).
 */
export function clearAdminToken(): void {
  adminAccessToken = null;
  if (typeof document !== "undefined") {
    document.cookie = `${ADMIN_SESSION_COOKIE}=; path=/admin; max-age=0`;
  }
}

// ─── Types ─────────────────────────────────────────────────────────────────────

/**
 * Admin user shape returned by POST /admin/auth/login.
 * Admins have no tenant, no permissions array, no feature flags.
 */
export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: "superadmin";
  totp_enabled: boolean;
  last_login_at: string | null;
  last_login_ip: string | null;
}

// ─── Auth Store ────────────────────────────────────────────────────────────────

interface AdminAuthState {
  /** Authenticated admin. Null when logged out. */
  admin: AdminUser | null;

  /**
   * Session identifier from the login response.
   * Used for display/audit purposes only; the real auth is the Bearer token.
   */
  session_id: string | null;

  /** True when admin + token are valid. */
  is_authenticated: boolean;

  /**
   * True during initial hydration check.
   * Because admin has no /auth/me endpoint, this starts as false —
   * the store is empty on reload and the admin must log in again.
   */
  is_loading: boolean;

  // ─── Actions ────────────────────────────────────────────────────────────────

  /** Called after a successful login. Populates admin state. */
  set_admin_auth: (admin: AdminUser, session_id: string) => void;

  /** Clears all admin auth state. Called on logout or 401. */
  clear_admin_auth: () => void;

  /** Sets the loading flag (used during TOTP step transitions). */
  set_loading: (loading: boolean) => void;
}

/**
 * Zustand store for admin authentication state.
 *
 * NOT persisted to localStorage. Starts empty on every page reload.
 * The admin must authenticate each browser session — this is intentional
 * for the high-privilege superadmin role.
 */
export const useAdminAuthStore = create<AdminAuthState>((set) => ({
  admin: null,
  session_id: null,
  is_authenticated: false,
  // Unlike the clinic layout, we start NOT loading — there is no /auth/me to call.
  // The layout treats an empty store as "unauthenticated → redirect to /admin/login".
  is_loading: false,

  set_admin_auth: (admin: AdminUser, session_id: string) => {
    set({
      admin,
      session_id,
      is_authenticated: true,
      is_loading: false,
    });
  },

  clear_admin_auth: () => {
    set({
      admin: null,
      session_id: null,
      is_authenticated: false,
      is_loading: false,
    });
  },

  set_loading: (loading: boolean) => {
    set({ is_loading: loading });
  },
}));

/**
 * Convenience hook — returns all admin auth state and actions.
 * Destructure only the fields needed to minimise re-renders.
 *
 * @example
 * const { admin, is_authenticated, clear_admin_auth } = useAdminAuth();
 */
export function useAdminAuth(): AdminAuthState {
  return useAdminAuthStore();
}
