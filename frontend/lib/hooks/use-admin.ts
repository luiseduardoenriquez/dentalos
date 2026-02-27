"use client";

/**
 * TanStack Query hooks for all admin API endpoints.
 *
 * Types match the backend Pydantic schemas in app/schemas/admin.py EXACTLY.
 * All queries use adminApiGet/adminApiPost/adminApiPut — never the clinic API client.
 * Query keys use an "admin" namespace prefix so they are isolated from clinic caches.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApiGet, adminApiPost, adminApiPut } from "@/lib/admin-api-client";
import {
  setAdminToken,
  useAdminAuthStore,
  type AdminUser,
} from "@/lib/hooks/use-admin-auth";

// ─── Auth Types (matches app/schemas/admin.py) ──────────────────────────────

export interface AdminLoginPayload {
  email: string;
  password: string;
  totp_code?: string;
}

/**
 * Backend: AdminLoginResponse
 *
 * access_token is always present (even if TOTP is pending — backend may
 * return a partial token or a full token depending on TOTP state).
 * totp_required: true means the admin must re-submit with totp_code.
 */
export interface AdminLoginResponse {
  access_token: string;
  token_type: string;
  admin_id: string;
  name: string;
  totp_required: boolean;
}

export interface AdminTOTPSetupResponse {
  secret: string;
  provisioning_uri: string;
  qr_code_base64: string | null;
}

export interface AdminTOTPVerifyPayload {
  totp_code: string;
}

// ─── Tenant Types (matches TenantSummary + TenantListResponse) ──────────────

export interface TenantSummary {
  id: string;
  name: string;
  slug: string;
  plan_name: string;
  status: string;
  user_count: number;
  patient_count: number;
  created_at: string;
}

export interface TenantListResponse {
  items: TenantSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminTenantsParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
}

// ─── Plan Types (matches PlanResponse + PlanUpdateRequest) ──────────────────

export interface PlanResponse {
  id: string;
  name: string;
  slug: string;
  price_cents: number;
  max_patients: number;
  max_doctors: number;
  features: Record<string, unknown>;
  is_active: boolean;
}

export interface PlanUpdatePayload {
  price_cents?: number;
  max_patients?: number;
  max_doctors?: number;
  features?: Record<string, unknown>;
  is_active?: boolean;
}

// ─── Analytics Types (matches PlatformAnalyticsResponse) ─────────────────────

export interface PlatformAnalyticsResponse {
  total_tenants: number;
  active_tenants: number;
  total_users: number;
  total_patients: number;
  mrr_cents: number;
  mau: number;
  churn_rate: number;
}

// ─── Feature Flag Types (matches FeatureFlagResponse + Create/Update) ───────

export interface FeatureFlagResponse {
  id: string;
  flag_name: string;
  scope: string | null;
  plan_filter: string | null;
  tenant_id: string | null;
  enabled: boolean;
  description: string | null;
}

export interface FeatureFlagCreatePayload {
  flag_name: string;
  enabled?: boolean;
  scope?: string;
  plan_filter?: string;
  tenant_id?: string;
  description?: string;
}

export interface FeatureFlagUpdatePayload {
  enabled?: boolean;
  scope?: string;
  plan_filter?: string;
  tenant_id?: string;
  description?: string;
}

// ─── Health Types (matches SystemHealthResponse) ─────────────────────────────

export interface SystemHealthResponse {
  status: string;
  postgres: boolean;
  redis: boolean;
  rabbitmq: boolean;
  storage: boolean;
  timestamp: string;
}

// ─── Impersonation Types (matches ImpersonateResponse) ──────────────────────

export interface ImpersonateResponse {
  access_token: string;
  token_type: string;
  tenant_id: string;
  impersonated_as: string;
}

// ─── Auth Hooks ──────────────────────────────────────────────────────────────

/**
 * Mutation for POST /admin/auth/login.
 *
 * If totp_required is true, the caller must show TOTP input and re-submit.
 * If totp_required is false, the login is complete — store token and redirect.
 */
export function useAdminLogin() {
  const set_admin_auth = useAdminAuthStore((s) => s.set_admin_auth);

  return useMutation({
    mutationFn: (payload: AdminLoginPayload) =>
      adminApiPost<AdminLoginResponse>("/admin/auth/login", payload),

    onSuccess: (data) => {
      if (data.totp_required) {
        return; // Caller handles TOTP step
      }
      setAdminToken(data.access_token);
      const adminUser: AdminUser = {
        id: data.admin_id,
        email: "", // Not returned by login endpoint
        name: data.name,
        role: "superadmin",
        totp_enabled: false,
        last_login_at: null,
        last_login_ip: null,
      };
      set_admin_auth(adminUser, data.admin_id);
    },
  });
}

/**
 * Mutation for POST /admin/auth/totp/setup.
 */
export function useAdminTOTPSetup() {
  return useMutation({
    mutationFn: () =>
      adminApiPost<AdminTOTPSetupResponse>("/admin/auth/totp/setup"),
  });
}

/**
 * Mutation for POST /admin/auth/totp/verify.
 */
export function useAdminTOTPVerify() {
  return useMutation({
    mutationFn: (payload: AdminTOTPVerifyPayload) =>
      adminApiPost<{ status: string }>("/admin/auth/totp/verify", payload),
  });
}

// ─── Tenant Hooks ────────────────────────────────────────────────────────────

/**
 * Query for GET /admin/tenants. Supports pagination, search, and status filter.
 */
export function useAdminTenants(params: AdminTenantsParams = {}) {
  return useQuery({
    queryKey: ["admin", "tenants", params],
    queryFn: () =>
      adminApiGet<TenantListResponse>("/admin/tenants", {
        page: params.page ?? 1,
        page_size: params.page_size ?? 20,
        ...(params.search ? { search: params.search } : {}),
        ...(params.status ? { status: params.status } : {}),
      }),
  });
}

/**
 * Mutation for POST /admin/tenants/{id}/impersonate.
 */
export function useImpersonateTenant() {
  return useMutation({
    mutationFn: (tenantId: string) =>
      adminApiPost<ImpersonateResponse>(
        `/admin/tenants/${tenantId}/impersonate`,
      ),
  });
}

// ─── Plan Hooks ──────────────────────────────────────────────────────────────

/**
 * Query for GET /admin/plans.
 */
export function useAdminPlans() {
  return useQuery({
    queryKey: ["admin", "plans"],
    queryFn: () => adminApiGet<PlanResponse[]>("/admin/plans"),
  });
}

/**
 * Mutation for PUT /admin/plans/{id}.
 */
export function useUpdatePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: PlanUpdatePayload }) =>
      adminApiPut<PlanResponse>(`/admin/plans/${id}`, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "plans"] });
    },
  });
}

// ─── Analytics Hooks ─────────────────────────────────────────────────────────

/**
 * Query for GET /admin/analytics.
 * Stale time: 5 minutes — data changes infrequently.
 */
export function useAdminAnalytics() {
  return useQuery({
    queryKey: ["admin", "analytics"],
    queryFn: () => adminApiGet<PlatformAnalyticsResponse>("/admin/analytics"),
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Feature Flag Hooks ──────────────────────────────────────────────────────

/**
 * Query for GET /admin/feature-flags.
 */
export function useAdminFeatureFlags() {
  return useQuery({
    queryKey: ["admin", "feature-flags"],
    queryFn: () => adminApiGet<FeatureFlagResponse[]>("/admin/feature-flags"),
  });
}

/**
 * Mutation for POST /admin/feature-flags.
 */
export function useCreateFeatureFlag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: FeatureFlagCreatePayload) =>
      adminApiPost<FeatureFlagResponse>("/admin/feature-flags", payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "feature-flags"] });
    },
  });
}

/**
 * Mutation for PUT /admin/feature-flags/{id}.
 */
export function useUpdateFeatureFlag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: FeatureFlagUpdatePayload;
    }) =>
      adminApiPut<FeatureFlagResponse>(`/admin/feature-flags/${id}`, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "feature-flags"] });
    },
  });
}

// ─── Health Hooks ────────────────────────────────────────────────────────────

/**
 * Query for GET /admin/health. Auto-refetches every 30 seconds.
 */
export function useAdminHealth() {
  return useQuery({
    queryKey: ["admin", "health"],
    queryFn: () => adminApiGet<SystemHealthResponse>("/admin/health"),
    refetchInterval: 30_000,
    staleTime: 0,
  });
}
