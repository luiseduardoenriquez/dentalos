"use client";

import { useMutation } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { setAccessToken } from "@/lib/auth";
import { useAuthStore } from "@/lib/hooks/use-auth";
import type { LoginFormValues } from "@/lib/validations/auth";
import type { TenantListItem, MeResponse } from "@/lib/hooks/use-auth";

// ─── Response Types ────────────────────────────────────────────────────────────

/**
 * Response from POST /auth/login.
 *
 * Two paths:
 * 1. Single-tenant user: access_token present, requires_tenant_selection = false.
 * 2. Multi-tenant user: requires_tenant_selection = true, tenants list returned.
 *    A second call to POST /auth/select-tenant is needed to get a tenant-scoped JWT.
 */
export interface LoginResponse {
  /** Present when login is complete (single clinic user). */
  access_token?: string;
  token_type?: string;
  expires_in?: number;
  /** Present when login is complete — user + tenant context. */
  user?: Record<string, unknown>;
  tenant?: Record<string, unknown>;
  /** True when the user belongs to multiple clinics and must pick one. */
  requires_tenant_selection?: boolean;
  /** Pre-auth token for tenant selection — only present when requires_tenant_selection = true. */
  pre_auth_token?: string;
  /** List of clinics — only present when requires_tenant_selection = true. */
  tenants?: TenantListItem[];
}

export interface SelectTenantResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: Record<string, unknown>;
  tenant: Record<string, unknown>;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Mutation hook for POST /auth/login.
 *
 * On success with a direct login (single tenant):
 *   - Stores the access token in memory.
 *   - Fetches /auth/me to hydrate the auth store.
 *
 * On success with multi-tenant (requires_tenant_selection = true):
 *   - Returns the tenants list so the caller can show the clinic selector.
 *   - Does NOT set auth state yet — caller must call useSelectTenant next.
 */
export function useLogin() {
  const set_auth = useAuthStore((s) => s.set_auth);

  return useMutation({
    mutationFn: (credentials: LoginFormValues) =>
      apiPost<LoginResponse>("/auth/login", credentials),

    onSuccess: async (data) => {
      // Direct login — single clinic or pre-selected tenant
      if (!data.requires_tenant_selection && data.access_token) {
        setAccessToken(data.access_token);
        const me = await apiGet<MeResponse>("/auth/me");
        set_auth(me);
      }
      // Multi-tenant: caller handles the tenant selection UI
      // Auth state is set after useSelectTenant resolves
    },
  });
}

// ─── Select Tenant Hook ────────────────────────────────────────────────────────

/**
 * Mutation hook for POST /auth/select-tenant.
 *
 * Called after a multi-clinic login to issue a tenant-scoped JWT.
 * On success, stores the token and fetches /auth/me to hydrate auth store.
 */
export function useSelectTenant() {
  const set_auth = useAuthStore((s) => s.set_auth);

  return useMutation({
    mutationFn: async (payload: {
      pre_auth_token: string;
      tenant_id: string;
    }) => {
      const data = await apiPost<SelectTenantResponse>(
        "/auth/select-tenant",
        payload,
      );
      // Store token immediately so /auth/me can use it
      setAccessToken(data.access_token);
      // Fetch full auth state (permissions, feature flags, plan limits)
      const me = await apiGet<MeResponse>("/auth/me");
      return me;
    },

    onSuccess: (me) => {
      set_auth(me);
    },
  });
}
