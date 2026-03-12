"use client";

/**
 * TanStack Query hooks for all admin API endpoints.
 *
 * Types match the backend Pydantic schemas in app/schemas/admin.py EXACTLY.
 * All queries use adminApiGet/adminApiPost/adminApiPut/adminApiDelete — never the clinic API client.
 * Query keys use an "admin" namespace prefix so they are isolated from clinic caches.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adminApiGet,
  adminApiPost,
  adminApiPut,
  adminApiDelete,
} from "@/lib/admin-api-client";
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
  doctor_count: number;
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
  planId?: string;
  countryCode?: string;
  createdAfter?: string;
  createdBefore?: string;
  sortBy?: string;
  sortOrder?: string;
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
  pricing_model: string;
  included_doctors: number;
  additional_doctor_price_cents: number;
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
  new_signups_30d: number;
  plan_distribution: { plan_name: string; count: number }[];
  top_tenants: {
    tenant_id: string;
    name: string;
    mrr_cents: number;
    patients: number;
  }[];
  country_distribution: { country: string; count: number }[];
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
  expires_at: string | null;
  reason: string | null;
}

export interface FeatureFlagCreatePayload {
  flag_name: string;
  enabled?: boolean;
  scope?: string;
  plan_filter?: string;
  tenant_id?: string;
  description?: string;
  expires_at?: string;
  reason?: string;
}

export interface FeatureFlagUpdatePayload {
  enabled?: boolean;
  scope?: string;
  plan_filter?: string;
  tenant_id?: string;
  description?: string;
  expires_at?: string;
  reason?: string;
}

// ─── Health Types (matches SystemHealthResponse) ─────────────────────────────

export interface SystemHealthResponse {
  status: string;
  postgres: boolean;
  redis: boolean;
  rabbitmq: boolean;
  storage: boolean;
  timestamp: string;
  service_details: Record<
    string,
    {
      healthy: boolean;
      latency_ms: number;
      version?: string;
      details?: Record<string, unknown>;
    }
  >;
}

// ─── Impersonation Types (matches ImpersonateResponse) ──────────────────────

export interface ImpersonatePayload {
  reason: string;
  duration_minutes?: number;
}

export interface ImpersonateResponse {
  access_token: string;
  token_type: string;
  tenant_id: string;
  impersonated_as: string;
  session_id: string | null;
  expires_at: string | null;
}

// ─── Audit Log Types ─────────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: string;
  admin_id: string;
  admin_email: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Plan Change History Types ───────────────────────────────────────────────

export interface PlanChangeHistoryEntry {
  id: string;
  plan_id: string;
  admin_id: string;
  field_changed: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export interface PlanChangeHistoryResponse {
  items: PlanChangeHistoryEntry[];
  total: number;
}

// ─── Flag Change History Types ───────────────────────────────────────────────

export interface FlagChangeHistoryEntry {
  id: string;
  flag_id: string;
  admin_id: string;
  field_changed: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

// ─── Superadmin Types ────────────────────────────────────────────────────────

export interface SuperadminResponse {
  id: string;
  email: string;
  name: string;
  totp_enabled: boolean;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface SuperadminCreatePayload {
  email: string;
  password: string;
  name: string;
}

export interface SuperadminUpdatePayload {
  name?: string;
  is_active?: boolean;
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

// ─── Tenant Detail Types (matches TenantDetailResponse) ──────────────────────

export interface TenantDetailResponse {
  id: string;
  name: string;
  slug: string;
  schema_name: string;
  owner_email: string;
  owner_user_id: string | null;
  country_code: string;
  timezone: string;
  currency_code: string;
  locale: string;
  plan_id: string;
  plan_name: string;
  status: string;
  phone: string | null;
  address: string | null;
  logo_url: string | null;
  onboarding_step: number;
  settings: Record<string, unknown>;
  addons: Record<string, unknown>;
  trial_ends_at: string | null;
  suspended_at: string | null;
  cancelled_at: string | null;
  user_count: number;
  created_at: string;
  updated_at: string;
}

export interface TenantCreatePayload {
  name: string;
  owner_email: string;
  plan_id: string;
  country_code?: string;
  timezone?: string;
  currency_code?: string;
}

export interface TenantUpdatePayload {
  name?: string;
  plan_id?: string;
  settings?: Record<string, unknown>;
  is_active?: boolean;
}

// ─── Tenant Hooks ────────────────────────────────────────────────────────────

/**
 * Query for GET /admin/tenants.
 * Supports pagination, search, status, plan, country, date range, and sort filters.
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
        ...(params.planId ? { plan_id: params.planId } : {}),
        ...(params.countryCode ? { country_code: params.countryCode } : {}),
        ...(params.createdAfter ? { created_after: params.createdAfter } : {}),
        ...(params.createdBefore
          ? { created_before: params.createdBefore }
          : {}),
        ...(params.sortBy ? { sort_by: params.sortBy } : {}),
        ...(params.sortOrder ? { sort_order: params.sortOrder } : {}),
      }),
  });
}

/**
 * Mutation for POST /admin/tenants/{id}/impersonate.
 * Accepts a reason and optional duration so the backend can audit the session.
 */
export function useImpersonateTenant() {
  return useMutation({
    mutationFn: ({
      tenantId,
      payload,
    }: {
      tenantId: string;
      payload: ImpersonatePayload;
    }) =>
      adminApiPost<ImpersonateResponse>(
        `/admin/tenants/${tenantId}/impersonate`,
        payload,
      ),
  });
}

/**
 * Query for GET /admin/tenants/{id}. Full tenant detail.
 */
export function useAdminTenantDetail(id: string) {
  return useQuery({
    queryKey: ["admin", "tenants", id],
    queryFn: () =>
      adminApiGet<TenantDetailResponse>(`/admin/tenants/${id}`),
    enabled: !!id,
  });
}

/**
 * Mutation for POST /admin/tenants. Creates a new clinic.
 */
export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: TenantCreatePayload) =>
      adminApiPost<TenantDetailResponse>("/admin/tenants", payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "tenants"] });
    },
  });
}

/**
 * Mutation for PUT /admin/tenants/{id}. Partial update.
 */
export function useUpdateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: TenantUpdatePayload;
    }) => adminApiPut<TenantDetailResponse>(`/admin/tenants/${id}`, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "tenants"] });
    },
  });
}

/**
 * Mutation for POST /admin/tenants/{id}/suspend. Toggles suspension.
 */
export function useSuspendTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (tenantId: string) =>
      adminApiPost<TenantDetailResponse>(
        `/admin/tenants/${tenantId}/suspend`,
      ),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "tenants"] });
    },
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

/**
 * Query for GET /admin/plans/{planId}/history.
 * Returns the full change history for a plan.
 */
export function usePlanChangeHistory(planId: string) {
  return useQuery({
    queryKey: ["admin", "plans", planId, "history"],
    queryFn: () =>
      adminApiGet<PlanChangeHistoryResponse>(
        `/admin/plans/${planId}/history`,
      ),
    enabled: !!planId,
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

/**
 * Query for GET /admin/feature-flags/{flagId}/history.
 * Returns the full change history for a feature flag.
 */
export function useFlagChangeHistory(flagId: string) {
  return useQuery({
    queryKey: ["admin", "feature-flags", flagId, "history"],
    queryFn: () =>
      adminApiGet<FlagChangeHistoryEntry[]>(
        `/admin/feature-flags/${flagId}/history`,
      ),
    enabled: !!flagId,
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

// ─── Audit Log Hooks ─────────────────────────────────────────────────────────

export interface AdminAuditLogParams {
  page: number;
  pageSize: number;
  action?: string;
  adminId?: string;
  dateFrom?: string;
  dateTo?: string;
}

/**
 * Query for GET /admin/audit-log.
 * Supports pagination and filtering by action, admin, and date range.
 */
export function useAdminAuditLog(params: AdminAuditLogParams) {
  return useQuery({
    queryKey: ["admin", "audit-log", params],
    queryFn: () =>
      adminApiGet<AuditLogListResponse>("/admin/audit-log", {
        page: params.page,
        page_size: params.pageSize,
        ...(params.action ? { action: params.action } : {}),
        ...(params.adminId ? { admin_id: params.adminId } : {}),
        ...(params.dateFrom ? { date_from: params.dateFrom } : {}),
        ...(params.dateTo ? { date_to: params.dateTo } : {}),
      }),
  });
}

// ─── Superadmin Management Hooks ─────────────────────────────────────────────

/**
 * Query for GET /admin/superadmins.
 */
export function useAdminSuperadmins() {
  return useQuery({
    queryKey: ["admin", "superadmins"],
    queryFn: () => adminApiGet<SuperadminResponse[]>("/admin/superadmins"),
  });
}

/**
 * Mutation for POST /admin/superadmins. Creates a new superadmin account.
 */
export function useCreateSuperadmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SuperadminCreatePayload) =>
      adminApiPost<SuperadminResponse>("/admin/superadmins", payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "superadmins"] });
    },
  });
}

/**
 * Mutation for PUT /admin/superadmins/{id}. Updates name or active status.
 */
export function useUpdateSuperadmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: SuperadminUpdatePayload;
    }) =>
      adminApiPut<SuperadminResponse>(`/admin/superadmins/${id}`, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "superadmins"] });
    },
  });
}

/**
 * Mutation for DELETE /admin/superadmins/{id}. Soft-deletes the superadmin account.
 */
export function useDeleteSuperadmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      adminApiDelete<{ status: string }>(`/admin/superadmins/${id}`),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "superadmins"] });
    },
  });
}

// ─── Export Hook ─────────────────────────────────────────────────────────────

/**
 * Mutation for GET /admin/export?export_type=...
 * Returns a Blob so the caller can trigger a browser download.
 * Used as a mutation (not a query) because export is an on-demand action.
 */
export function useExportData() {
  return useMutation({
    mutationFn: (exportType: string) =>
      adminApiGet<Blob>("/admin/export", { export_type: exportType }),
  });
}

// ── Notification Types ──────────────────────────────────────────────────────

export interface AdminNotificationItem {
  id: string;
  admin_id: string | null;
  title: string;
  message: string;
  notification_type: string; // info, warning, error, success
  resource_type: string | null;
  resource_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface AdminNotificationListResponse {
  items: AdminNotificationItem[];
  unread_count: number;
  total: number;
}

// ── Notification Hooks ──────────────────────────────────────────────────────

/**
 * Query for GET /admin/notifications.
 * Auto-refetches every 60 seconds to pick up new notifications.
 */
export function useAdminNotifications(
  params: { page?: number; pageSize?: number; unreadOnly?: boolean } = {},
) {
  return useQuery({
    queryKey: ["admin", "notifications", params],
    queryFn: () =>
      adminApiGet<AdminNotificationListResponse>("/admin/notifications", {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,
        ...(params.unreadOnly ? { unread_only: true } : {}),
      }),
    refetchInterval: 60_000,
  });
}

/**
 * Mutation for POST /admin/notifications/{id}/read.
 */
export function useMarkNotificationRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) =>
      adminApiPost<{ status: string }>(
        `/admin/notifications/${notificationId}/read`,
      ),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "notifications"] });
    },
  });
}

/**
 * Mutation for POST /admin/notifications/read-all.
 */
export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      adminApiPost<{ status: string; marked_count: number }>(
        "/admin/notifications/read-all",
      ),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "notifications"] });
    },
  });
}
