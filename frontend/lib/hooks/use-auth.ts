"use client";

import { create } from "zustand";
import { clearAccessToken } from "@/lib/auth";

// ─── Backend Response Types (snake_case — never convert to camelCase) ──────────

/**
 * Matches backend UserResponse schema in app/schemas/auth.py
 */
export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  phone: string | null;
  avatar_url: string | null;
  professional_license: string | null;
  specialties: string[] | null;
  is_active: boolean;
  email_verified: boolean;
}

/**
 * Matches backend TenantResponse schema in app/schemas/auth.py
 */
export interface Tenant {
  id: string;
  slug: string;
  name: string;
  country_code: string;
  timezone: string;
  currency_code: string;
  status: string;
  plan_name: string;
  logo_url: string | null;
}

/**
 * Matches backend TenantListItem schema — used on the clinic selector screen.
 * Returned by POST /auth/login when the user belongs to multiple clinics.
 */
export interface TenantListItem {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: string;
  is_primary: boolean;
}

/**
 * Plan limits returned by GET /auth/me — used to enforce frontend plan gates.
 */
export interface PlanLimits {
  max_patients: number;
  max_doctors: number;
  max_users: number;
  max_storage_mb: number;
}

/**
 * Full /auth/me response — includes permissions and feature flags.
 */
export interface MeResponse {
  user: User;
  tenant: Tenant;
  permissions: string[];
  feature_flags: Record<string, boolean>;
  plan_limits: PlanLimits;
}

// ─── Auth Store ────────────────────────────────────────────────────────────────

interface AuthState {
  /** Currently authenticated user. Null when logged out or loading. */
  user: User | null;

  /** Currently selected tenant (clinic). Null when logged out or loading. */
  tenant: Tenant | null;

  /** Granular permissions list from the JWT / /auth/me response. */
  permissions: string[];

  /** Feature flags for plan-gated features. */
  feature_flags: Record<string, boolean>;

  /** Plan limits for plan-gated UI elements (e.g. disable add patient if at limit). */
  plan_limits: PlanLimits | null;

  /** True when user + tenant are fully loaded and valid. */
  is_authenticated: boolean;

  /**
   * True during initial auth check (page load rehydration via /auth/me).
   * Use to show a full-page loading spinner instead of flashing the login page.
   */
  is_loading: boolean;

  // ─── Actions ──────────────────────────────────────────────────────────────

  /**
   * Stores auth state after a successful login or /auth/me rehydration.
   *
   * @param me - Full MeResponse from the backend
   */
  set_auth: (me: MeResponse) => void;

  /**
   * Clears all auth state. Called on logout or when token refresh fails.
   */
  clear_auth: () => void;

  /**
   * Sets the loading flag during initial auth check.
   *
   * @param loading - Whether the auth check is in progress
   */
  set_loading: (loading: boolean) => void;

  /**
   * Checks if the current user has a specific permission.
   * Format: "resource:action" (e.g. "patients:write", "odontogram:read")
   *
   * @param permission - Permission string to check
   */
  has_permission: (permission: string) => boolean;

  /**
   * Checks if the current user has one of the given roles.
   *
   * @param roles - One or more role codes to check against
   */
  has_role: (...roles: string[]) => boolean;

  /**
   * Checks if a feature flag is enabled for the current tenant's plan.
   *
   * @param flag - Feature flag key (e.g. "voice_dictation", "radiograph_ai")
   */
  has_feature: (flag: string) => boolean;
}

const INITIAL_PLAN_LIMITS: PlanLimits = {
  max_patients: 0,
  max_doctors: 0,
  max_users: 0,
  max_storage_mb: 0,
};

/**
 * Global auth store using Zustand.
 *
 * NOT persisted to localStorage — access tokens live in memory only.
 * On page reload, the store starts empty and useAuthRehydration (in the
 * layout) calls /auth/me to restore state using the HttpOnly refresh cookie.
 */
export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  tenant: null,
  permissions: [],
  feature_flags: {},
  plan_limits: null,
  is_authenticated: false,
  is_loading: true, // Start as loading — assume we need to check auth

  set_auth: (me: MeResponse) => {
    set({
      user: me.user,
      tenant: me.tenant,
      permissions: me.permissions,
      feature_flags: me.feature_flags,
      plan_limits: me.plan_limits,
      is_authenticated: true,
      is_loading: false,
    });
  },

  clear_auth: () => {
    clearAccessToken();
    set({
      user: null,
      tenant: null,
      permissions: [],
      feature_flags: {},
      plan_limits: INITIAL_PLAN_LIMITS,
      is_authenticated: false,
      is_loading: false,
    });
  },

  set_loading: (loading: boolean) => {
    set({ is_loading: loading });
  },

  has_permission: (permission: string) => {
    return get().permissions.includes(permission);
  },

  has_role: (...roles: string[]) => {
    const user = get().user;
    if (!user) return false;
    return roles.includes(user.role);
  },

  has_feature: (flag: string) => {
    return get().feature_flags[flag] === true;
  },
}));

/**
 * Convenience hook — returns all auth state and actions.
 * Components should destructure only the fields they need to minimize re-renders.
 *
 * @example
 * const { user, is_authenticated, has_permission } = useAuth();
 * if (has_permission("patients:write")) { ... }
 */
export function useAuth(): AuthState {
  return useAuthStore();
}
