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

// ─── Trial Management Types (SA-R02) ────────────────────────────────────────

export interface TrialTenantItem {
  id: string;
  name: string;
  slug: string;
  plan_name: string;
  status: string;
  owner_email: string;
  trial_ends_at: string | null;
  days_remaining: number | null;
  created_at: string;
}

export interface TrialListResponse {
  items: TrialTenantItem[];
  total: number;
  expiring_soon_count: number;
  conversion_rate: number;
  avg_days_to_conversion: number;
}

// ─── Trial Management Hooks ─────────────────────────────────────────────────

export function useAdminTrials() {
  return useQuery({
    queryKey: ["admin", "trials"],
    queryFn: () => adminApiGet<TrialListResponse>("/admin/trials"),
    staleTime: 2 * 60 * 1000,
  });
}

export function useExtendTrial() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      tenantId,
      days,
    }: {
      tenantId: string;
      days: number;
    }) =>
      adminApiPost<{ tenant_id: string; trial_ends_at: string; days_added: number }>(
        `/admin/tenants/${tenantId}/extend-trial`,
        { days },
      ),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "trials"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "tenants"] });
    },
  });
}

// ─── Maintenance Mode Types (SA-O04) ────────────────────────────────────────

export interface MaintenanceStatusResponse {
  enabled: boolean;
  message: string | null;
  scheduled_end: string | null;
  updated_at: string | null;
}

// ─── Maintenance Mode Hooks ─────────────────────────────────────────────────

export function useMaintenanceStatus() {
  return useQuery({
    queryKey: ["admin", "maintenance"],
    queryFn: () =>
      adminApiGet<MaintenanceStatusResponse>("/admin/maintenance"),
    refetchInterval: 30_000,
  });
}

export function useToggleMaintenance() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: {
      enabled: boolean;
      message?: string;
      scheduled_end?: string;
    }) =>
      adminApiPost<MaintenanceStatusResponse>("/admin/maintenance", payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "maintenance"] });
    },
  });
}

// ─── Job Monitor Types (SA-O01) ─────────────────────────────────────────────

export interface QueueStatItem {
  name: string;
  connected: boolean;
  messages_ready: number;
  consumers: number;
}

export interface JobMonitorResponse {
  connected: boolean;
  exchange: string;
  queues: QueueStatItem[];
}

// ─── Job Monitor Hooks ──────────────────────────────────────────────────────

export function useAdminJobs() {
  return useQuery({
    queryKey: ["admin", "jobs"],
    queryFn: () => adminApiGet<JobMonitorResponse>("/admin/jobs"),
    refetchInterval: 15_000,
  });
}

// ─── Announcement Types (SA-E01) ────────────────────────────────────────────

export interface AnnouncementResponse {
  id: string;
  title: string;
  body: string;
  announcement_type: string;
  visibility: string;
  visibility_filter: Record<string, unknown>;
  is_dismissable: boolean;
  is_active: boolean;
  starts_at: string | null;
  ends_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AnnouncementListResponse {
  items: AnnouncementResponse[];
  total: number;
}

export interface AnnouncementCreatePayload {
  title: string;
  body: string;
  announcement_type?: string;
  visibility?: string;
  visibility_filter?: Record<string, unknown>;
  is_dismissable?: boolean;
  starts_at?: string;
  ends_at?: string;
}

export interface AnnouncementUpdatePayload {
  title?: string;
  body?: string;
  announcement_type?: string;
  visibility?: string;
  visibility_filter?: Record<string, unknown>;
  is_dismissable?: boolean;
  is_active?: boolean;
  starts_at?: string;
  ends_at?: string;
}

// ─── Announcement Hooks ─────────────────────────────────────────────────────

export function useAdminAnnouncements(activeOnly = false) {
  return useQuery({
    queryKey: ["admin", "announcements", { activeOnly }],
    queryFn: () =>
      adminApiGet<AnnouncementListResponse>("/admin/announcements", {
        ...(activeOnly ? { active_only: true } : {}),
      }),
  });
}

export function useCreateAnnouncement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: AnnouncementCreatePayload) =>
      adminApiPost<AnnouncementResponse>("/admin/announcements", payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "announcements"] });
    },
  });
}

export function useUpdateAnnouncement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: AnnouncementUpdatePayload;
    }) =>
      adminApiPut<AnnouncementResponse>(
        `/admin/announcements/${id}`,
        payload,
      ),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "announcements"] });
    },
  });
}

export function useDeleteAnnouncement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      adminApiDelete<{ status: string }>(`/admin/announcements/${id}`),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "announcements"] });
    },
  });
}

// ─── Revenue Dashboard Types (SA-R01) ───────────────────────────────────────

export interface RevenueMonthDataPoint {
  month: string;
  mrr_cents: number;
  active_tenants: number;
  churned_tenants: number;
  new_tenants: number;
  addon_revenue_cents: number;
}

export interface RevenuePlanBreakdown {
  plan_name: string;
  mrr_cents: number;
  tenant_count: number;
}

export interface RevenueCountryBreakdown {
  country: string;
  mrr_cents: number;
  tenant_count: number;
}

export interface RevenueKPIs {
  current_mrr_cents: number;
  previous_mrr_cents: number;
  mrr_growth_pct: number;
  arpa_cents: number;
  ltv_cents: number;
  nrr_pct: number;
  total_addon_revenue_cents: number;
}

export interface RevenueDashboardResponse {
  kpis: RevenueKPIs;
  monthly_trend: RevenueMonthDataPoint[];
  plan_breakdown: RevenuePlanBreakdown[];
  country_breakdown: RevenueCountryBreakdown[];
}

// ─── Revenue Dashboard Hooks ────────────────────────────────────────────────

export function useRevenueDashboard(months = 12) {
  return useQuery({
    queryKey: ["admin", "revenue", months],
    queryFn: () =>
      adminApiGet<RevenueDashboardResponse>("/admin/analytics/revenue", {
        months,
      }),
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Add-on Usage Types (SA-R03) ────────────────────────────────────────────

export interface AddonTenantUsage {
  tenant_id: string;
  tenant_name: string;
  plan_name: string;
  voice_enabled: boolean;
  radiograph_enabled: boolean;
}

export interface AddonMetrics {
  total_eligible_tenants: number;
  voice_adoption_count: number;
  voice_adoption_pct: number;
  radiograph_adoption_count: number;
  radiograph_adoption_pct: number;
  total_addon_revenue_cents: number;
  upsell_candidates: number;
}

export interface AddonUsageResponse {
  metrics: AddonMetrics;
  tenants: AddonTenantUsage[];
}

// ─── Add-on Usage Hooks ─────────────────────────────────────────────────────

export function useAddonUsage() {
  return useQuery({
    queryKey: ["admin", "addons"],
    queryFn: () => adminApiGet<AddonUsageResponse>("/admin/analytics/addons"),
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Onboarding Funnel Types (SA-G03) ───────────────────────────────────────

export interface OnboardingStepMetric {
  step: number;
  label: string;
  tenant_count: number;
  pct_of_total: number;
}

export interface OnboardingFunnelResponse {
  total_tenants: number;
  steps: OnboardingStepMetric[];
  stuck_tenants: {
    tenant_id: string;
    name: string;
    step: number;
    owner_email: string;
    days_since_signup: number;
  }[];
}

// ─── Onboarding Funnel Hooks ────────────────────────────────────────────────

export function useOnboardingFunnel() {
  return useQuery({
    queryKey: ["admin", "onboarding"],
    queryFn: () =>
      adminApiGet<OnboardingFunnelResponse>("/admin/analytics/onboarding"),
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Cross-Tenant User Search Types (SA-U01) ──────────────────────────────

export interface CrossTenantUserItem {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  tenant_id: string;
  tenant_name: string;
  status: string;
  last_login_at: string | null;
  is_multi_clinic: boolean;
}

export interface CrossTenantUserListResponse {
  items: CrossTenantUserItem[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Cross-Tenant User Search Hooks ───────────────────────────────────────

export function useCrossTenantUserSearch(
  search: string,
  page: number = 1,
  pageSize: number = 20,
  role?: string
) {
  return useQuery({
    queryKey: ["admin", "users", search, page, pageSize, role],
    queryFn: () => {
      const params = new URLSearchParams({
        search,
        page: String(page),
        page_size: String(pageSize),
      });
      if (role) params.set("role", role);
      return adminApiGet<CrossTenantUserListResponse>(
        `/admin/users?${params.toString()}`
      );
    },
    enabled: search.length >= 2,
    staleTime: 30 * 1000,
  });
}

// ─── Database Metrics Types (SA-O02) ──────────────────────────────────────

export interface TableSizeItem {
  schema_name: string;
  table_name: string;
  total_size: string;
  row_count: number;
}

export interface SlowQueryItem {
  query: string;
  calls: number;
  mean_time_ms: number;
  total_time_ms: number;
}

export interface DatabaseMetricsResponse {
  total_db_size: string;
  schema_count: number;
  connection_pool_active: number;
  connection_pool_idle: number;
  connection_pool_max: number;
  index_hit_ratio: number;
  cache_hit_ratio: number;
  largest_tables: TableSizeItem[];
  slow_queries: SlowQueryItem[];
  dead_tuples_total: number;
}

// ─── Database Metrics Hooks ───────────────────────────────────────────────

export function useDatabaseMetrics() {
  return useQuery({
    queryKey: ["admin", "database-metrics"],
    queryFn: () =>
      adminApiGet<DatabaseMetricsResponse>("/admin/metrics/database"),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 60 * 1000,
  });
}

// ─── Bulk Operations Types (SA-A03) ───────────────────────────────────────

export interface BulkOperationResult {
  tenant_id: string;
  tenant_name: string;
  success: boolean;
  error: string | null;
}

export interface BulkOperationResponse {
  total: number;
  succeeded: number;
  failed: number;
  results: BulkOperationResult[];
}

// ─── Bulk Operations Hooks ────────────────────────────────────────────────

export function useBulkTenantOperation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      tenant_ids: string[];
      action: string;
      plan_id?: string;
      trial_days?: number;
    }) => adminApiPost<BulkOperationResponse>("/admin/tenants/bulk", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "tenants"] });
      qc.invalidateQueries({ queryKey: ["admin", "analytics"] });
    },
  });
}

// ─── Compliance Dashboard Types (SA-C01) ──────────────────────────────────

export interface TenantComplianceItem {
  tenant_id: string;
  tenant_name: string;
  country_code: string;
  rips_status: string;
  rda_status: string;
  consent_templates_count: number;
  consent_templates_required: number;
  doctors_verified: number;
  doctors_total: number;
  last_rips_at: string | null;
  last_rda_at: string | null;
}

export interface ComplianceKPIs {
  total_colombian_tenants: number;
  rips_compliant: number;
  rips_compliant_pct: number;
  rda_compliant: number;
  rda_compliant_pct: number;
  consent_compliant: number;
  consent_compliant_pct: number;
  rethus_verified_pct: number;
}

export interface ComplianceDashboardResponse {
  kpis: ComplianceKPIs;
  tenants: TenantComplianceItem[];
}

// ─── Compliance Dashboard Hooks ───────────────────────────────────────────

export function useComplianceDashboard() {
  return useQuery({
    queryKey: ["admin", "compliance"],
    queryFn: () =>
      adminApiGet<ComplianceDashboardResponse>("/admin/compliance"),
    staleTime: 10 * 60 * 1000,
  });
}

// ─── Security Alerts Types (SA-C02) ───────────────────────────────────────

export interface SecurityAlertItem {
  id: string;
  alert_type: string;
  severity: string;
  message: string;
  source_ip: string | null;
  admin_id: string | null;
  tenant_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SecurityAlertListResponse {
  items: SecurityAlertItem[];
  total: number;
  failed_logins_24h: number;
  suspicious_ips: number;
  after_hours_actions: number;
}

// ─── Security Alerts Hooks ────────────────────────────────────────────────

export function useSecurityAlerts(page: number = 1, pageSize: number = 50) {
  return useQuery({
    queryKey: ["admin", "security-alerts", page, pageSize],
    queryFn: () =>
      adminApiGet<SecurityAlertListResponse>(
        `/admin/security/alerts?page=${page}&page_size=${pageSize}`
      ),
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

// ─── Data Retention Types (SA-C03) ────────────────────────────────────────

export interface RetentionPolicyItem {
  data_type: string;
  description: string;
  retention_days: number;
  current_oldest: string | null;
  records_eligible: number;
}

export interface ArchivableTenantItem {
  tenant_id: string;
  tenant_name: string;
  status: string;
  cancelled_at: string | null;
  days_since_cancelled: number;
}

export interface DataRetentionResponse {
  policies: RetentionPolicyItem[];
  archivable_tenants: ArchivableTenantItem[];
  total_archivable: number;
}

// ─── Data Retention Hooks ─────────────────────────────────────────────────

export function useDataRetention() {
  return useQuery({
    queryKey: ["admin", "data-retention"],
    queryFn: () => adminApiGet<DataRetentionResponse>("/admin/retention"),
    staleTime: 10 * 60 * 1000,
  });
}

// ─── Tenant Usage Analytics Types (SA-U02) ────────────────────────────────

export interface TenantUsageMetrics {
  tenant_id: string;
  tenant_name: string;
  plan_name: string;
  active_users_7d: number;
  patients_created_30d: number;
  appointments_30d: number;
  invoices_30d: number;
  clinical_records_30d: number;
  health_score: number;
  risk_level: string;
}

export interface TenantHealthListResponse {
  items: TenantUsageMetrics[];
  total: number;
  healthy_count: number;
  at_risk_count: number;
  critical_count: number;
}

// ─── Tenant Usage Analytics Hooks ─────────────────────────────────────────

export function useTenantHealth() {
  return useQuery({
    queryKey: ["admin", "tenant-health"],
    queryFn: () =>
      adminApiGet<TenantHealthListResponse>("/admin/analytics/tenant-health"),
    staleTime: 10 * 60 * 1000,
  });
}

// ─── Cohort Analysis Types (SA-G01) ───────────────────────────────────────

export interface CohortRow {
  cohort_month: string;
  signup_count: number;
  retention: number[];
}

export interface CohortAnalysisResponse {
  cohorts: CohortRow[];
  months_tracked: number;
  avg_churn_month: number;
}

// ─── Cohort Analysis Hooks ────────────────────────────────────────────────

export function useCohortAnalysis(months: number = 12) {
  return useQuery({
    queryKey: ["admin", "cohorts", months],
    queryFn: () =>
      adminApiGet<CohortAnalysisResponse>(
        `/admin/analytics/cohorts?months=${months}`
      ),
    staleTime: 30 * 60 * 1000,
  });
}

// ─── Feature Adoption Types (SA-G02) ──────────────────────────────────────

export interface TenantFeatureUsage {
  tenant_id: string;
  tenant_name: string;
  plan_name: string;
  odontogram: boolean;
  appointments: boolean;
  billing: boolean;
  portal: boolean;
  whatsapp: boolean;
  voice: boolean;
  ai_reports: boolean;
  telemedicine: boolean;
  features_used: number;
  features_total: number;
}

export interface FeatureAdoptionSummary {
  feature_name: string;
  adoption_count: number;
  adoption_pct: number;
}

export interface FeatureAdoptionResponse {
  summary: FeatureAdoptionSummary[];
  tenants: TenantFeatureUsage[];
  total_tenants: number;
}

// ─── Feature Adoption Hooks ───────────────────────────────────────────────

export function useFeatureAdoption() {
  return useQuery({
    queryKey: ["admin", "feature-adoption"],
    queryFn: () =>
      adminApiGet<FeatureAdoptionResponse>(
        "/admin/analytics/feature-adoption"
      ),
    staleTime: 10 * 60 * 1000,
  });
}

// ─── Broadcast Messaging Types (SA-E02) ───────────────────────────────────

export interface BroadcastHistoryItem {
  id: string;
  subject: string;
  body: string;
  template: string | null;
  filter_plan: string | null;
  filter_country: string | null;
  filter_status: string | null;
  recipients_count: number;
  sent_by: string;
  created_at: string;
}

export interface BroadcastHistoryResponse {
  items: BroadcastHistoryItem[];
  total: number;
}

export interface BroadcastSendResponse {
  broadcast_id: string;
  recipients_count: number;
  status: string;
}

// ─── Broadcast Messaging Hooks ────────────────────────────────────────────

export function useBroadcastHistory(page: number = 1) {
  return useQuery({
    queryKey: ["admin", "broadcast-history", page],
    queryFn: () =>
      adminApiGet<BroadcastHistoryResponse>(
        `/admin/broadcast/history?page=${page}`
      ),
    staleTime: 30 * 1000,
  });
}

export function useSendBroadcast() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      subject: string;
      body: string;
      template?: string;
      filter_plan?: string;
      filter_country?: string;
      filter_status?: string;
    }) => adminApiPost<BroadcastSendResponse>("/admin/broadcast", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "broadcast-history"] });
    },
  });
}

// ─── Alert Rules Types (SA-A01) ───────────────────────────────────────────

export interface AlertRuleResponse {
  id: string;
  name: string;
  condition: string;
  threshold: string;
  channel: string;
  is_active: boolean;
  last_triggered_at: string | null;
  created_at: string;
}

export interface AlertRuleListResponse {
  items: AlertRuleResponse[];
  total: number;
}

// ─── Alert Rules Hooks ────────────────────────────────────────────────────

export function useAlertRules() {
  return useQuery({
    queryKey: ["admin", "alert-rules"],
    queryFn: () =>
      adminApiGet<AlertRuleListResponse>("/admin/alert-rules"),
    staleTime: 60 * 1000,
  });
}

export function useCreateAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      condition: string;
      threshold: string;
      channel?: string;
      is_active?: boolean;
    }) => adminApiPost<AlertRuleResponse>("/admin/alert-rules", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "alert-rules"] });
    },
  });
}

export function useUpdateAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) =>
      adminApiPut<AlertRuleResponse>(`/admin/alert-rules/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "alert-rules"] });
    },
  });
}

export function useDeleteAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      adminApiDelete<{ status: string }>(`/admin/alert-rules/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "alert-rules"] });
    },
  });
}

// ─── Scheduled Reports Types (SA-A02) ─────────────────────────────────────

export interface ScheduledReportResponse {
  id: string;
  name: string;
  report_type: string;
  schedule: string;
  recipients: string[];
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export interface ScheduledReportListResponse {
  items: ScheduledReportResponse[];
  total: number;
}

// ─── Scheduled Reports Hooks ──────────────────────────────────────────────

export function useScheduledReports() {
  return useQuery({
    queryKey: ["admin", "scheduled-reports"],
    queryFn: () =>
      adminApiGet<ScheduledReportListResponse>("/admin/scheduled-reports"),
    staleTime: 60 * 1000,
  });
}

export function useCreateScheduledReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      report_type: string;
      schedule: string;
      recipients: string[];
      is_active?: boolean;
    }) =>
      adminApiPost<ScheduledReportResponse>("/admin/scheduled-reports", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "scheduled-reports"] });
    },
  });
}

export function useUpdateScheduledReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) =>
      adminApiPut<ScheduledReportResponse>(
        `/admin/scheduled-reports/${id}`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "scheduled-reports"] });
    },
  });
}

export function useDeleteScheduledReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      adminApiDelete<{ status: string }>(`/admin/scheduled-reports/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "scheduled-reports"] });
    },
  });
}

// ─── Support Chat Types (SA-E03) ──────────────────────────────────────────

export interface SupportThreadItem {
  id: string;
  tenant_id: string;
  tenant_name: string;
  last_message: string | null;
  last_message_at: string | null;
  unread_count: number;
  status: string;
  created_at: string;
}

export interface SupportMessageItem {
  id: string;
  thread_id: string;
  sender_type: string;
  sender_name: string;
  content: string;
  created_at: string;
}

export interface SupportThreadListResponse {
  items: SupportThreadItem[];
  total: number;
  unread_total: number;
}

export interface SupportThreadDetailResponse {
  thread: SupportThreadItem;
  messages: SupportMessageItem[];
}

// ─── Support Chat Hooks ───────────────────────────────────────────────────

export function useSupportThreads() {
  return useQuery({
    queryKey: ["admin", "support-threads"],
    queryFn: () =>
      adminApiGet<SupportThreadListResponse>("/admin/support/threads"),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useSupportThread(tenantId: string) {
  return useQuery({
    queryKey: ["admin", "support-thread", tenantId],
    queryFn: () =>
      adminApiGet<SupportThreadDetailResponse>(
        `/admin/support/threads/${tenantId}`
      ),
    enabled: !!tenantId,
    staleTime: 10 * 1000,
    refetchInterval: 15 * 1000,
  });
}

export function useSendSupportMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      tenantId,
      content,
    }: {
      tenantId: string;
      content: string;
    }) =>
      adminApiPost<SupportMessageItem>(
        `/admin/support/threads/${tenantId}/messages`,
        { content }
      ),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({
        queryKey: ["admin", "support-thread", variables.tenantId],
      });
      qc.invalidateQueries({ queryKey: ["admin", "support-threads"] });
    },
  });
}


// ─── SA-K01: Catalog Administration ─────────────────────────────────────

export interface CatalogCodeItem {
  id: string;
  code: string;
  description: string;
  category: string | null;
  created_at: string;
  updated_at: string;
}

export interface CatalogCodeListResponse {
  items: CatalogCodeItem[];
  total: number;
  page: number;
  page_size: number;
}

export function useCatalogCodes(
  catalogType: "cie10" | "cups",
  params: { search?: string; page?: number; page_size?: number } = {}
) {
  const qs = new URLSearchParams();
  if (params.search) qs.set("search", params.search);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString();
  return useQuery({
    queryKey: ["admin", "catalog", catalogType, params],
    queryFn: () =>
      adminApiGet<CatalogCodeListResponse>(
        `/admin/catalog/${catalogType}${query ? `?${query}` : ""}`
      ),
    staleTime: 60 * 1000,
  });
}

export function useCreateCatalogCode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      catalogType,
      data,
    }: {
      catalogType: "cie10" | "cups";
      data: { code: string; description: string; category?: string };
    }) => adminApiPost<CatalogCodeItem>(`/admin/catalog/${catalogType}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "catalog"] });
    },
  });
}

export function useUpdateCatalogCode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      catalogType,
      codeId,
      data,
    }: {
      catalogType: "cie10" | "cups";
      codeId: string;
      data: { description?: string; category?: string };
    }) =>
      adminApiPut<CatalogCodeItem>(
        `/admin/catalog/${catalogType}/${codeId}`,
        data
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "catalog"] });
    },
  });
}


// ─── SA-K02: Global Template Management ─────────────────────────────────

export interface GlobalTemplateItem {
  id: string;
  name: string;
  template_type: string;
  category: string | null;
  version: number;
  is_active: boolean;
  tenant_override_count: number;
  created_at: string;
  updated_at: string;
}

export interface GlobalTemplateDetailResponse {
  id: string;
  name: string;
  template_type: string;
  category: string | null;
  content: string;
  version: number;
  is_active: boolean;
  tenant_override_count: number;
  created_at: string;
  updated_at: string;
}

export interface GlobalTemplateListResponse {
  items: GlobalTemplateItem[];
  total: number;
}

export function useGlobalTemplates(templateType?: string) {
  const qs = templateType ? `?template_type=${templateType}` : "";
  return useQuery({
    queryKey: ["admin", "templates", templateType],
    queryFn: () =>
      adminApiGet<GlobalTemplateListResponse>(`/admin/templates${qs}`),
    staleTime: 60 * 1000,
  });
}

export function useGlobalTemplate(templateId: string, templateType = "consent") {
  return useQuery({
    queryKey: ["admin", "template", templateId],
    queryFn: () =>
      adminApiGet<GlobalTemplateDetailResponse>(
        `/admin/templates/${templateId}?template_type=${templateType}`
      ),
    enabled: !!templateId,
    staleTime: 60 * 1000,
  });
}

export function useUpdateGlobalTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      templateId,
      templateType,
      data,
    }: {
      templateId: string;
      templateType?: string;
      data: {
        name?: string;
        content?: string;
        category?: string;
        is_active?: boolean;
      };
    }) =>
      adminApiPut<GlobalTemplateDetailResponse>(
        `/admin/templates/${templateId}?template_type=${templateType || "consent"}`,
        data
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "templates"] });
      qc.invalidateQueries({ queryKey: ["admin", "template"] });
    },
  });
}


// ─── SA-K03: Default Price Catalog ──────────────────────────────────────

export interface DefaultPriceItem {
  id: string;
  cups_code: string;
  cups_description: string;
  country_code: string;
  price_cents: number;
  currency_code: string;
  is_active: boolean;
  updated_at: string;
}

export interface DefaultPriceListResponse {
  items: DefaultPriceItem[];
  total: number;
  page: number;
  page_size: number;
}

export function useDefaultPrices(params: {
  country_code?: string;
  search?: string;
  page?: number;
  page_size?: number;
} = {}) {
  const qs = new URLSearchParams();
  if (params.country_code) qs.set("country_code", params.country_code);
  if (params.search) qs.set("search", params.search);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString();
  return useQuery({
    queryKey: ["admin", "default-prices", params],
    queryFn: () =>
      adminApiGet<DefaultPriceListResponse>(
        `/admin/catalog/prices${query ? `?${query}` : ""}`
      ),
    staleTime: 60 * 1000,
  });
}

export function useUpsertDefaultPrice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      cups_code: string;
      cups_description: string;
      country_code?: string;
      price_cents: number;
      currency_code?: string;
    }) => adminApiPost<DefaultPriceItem>("/admin/catalog/prices", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "default-prices"] });
    },
  });
}


// ─── SA-U03: Tenant Comparison ──────────────────────────────────────────

export interface TenantBenchmarkItem {
  tenant_id: string;
  tenant_name: string;
  plan_name: string;
  patients: number;
  active_users: number;
  appointments_30d: number;
  invoices_30d: number;
  mrr_cents: number;
  features_used: number;
}

export interface TenantComparisonResponse {
  tenants: TenantBenchmarkItem[];
  plan_averages: Record<string, number>;
}

export function useTenantComparison(tenantIds: string[]) {
  const ids = tenantIds.join(",");
  return useQuery({
    queryKey: ["admin", "benchmark", tenantIds],
    queryFn: () =>
      adminApiGet<TenantComparisonResponse>(
        `/admin/analytics/benchmark?tenant_ids=${encodeURIComponent(ids)}`
      ),
    enabled: tenantIds.length >= 2,
    staleTime: 30 * 1000,
  });
}


// ─── SA-O03: API Usage Metrics ──────────────────────────────────────────

export interface ApiEndpointMetric {
  endpoint: string;
  method: string;
  count: number;
  avg_latency_ms: number;
  error_count: number;
}

export interface ApiTenantUsage {
  tenant_id: string;
  tenant_name: string;
  request_count: number;
}

export interface ApiUsageMetricsResponse {
  total_requests_24h: number;
  error_rate_percent: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  top_endpoints: ApiEndpointMetric[];
  top_tenants: ApiTenantUsage[];
  requests_by_hour: { hour: string; count: number }[];
}

export function useApiUsageMetrics() {
  return useQuery({
    queryKey: ["admin", "api-metrics"],
    queryFn: () =>
      adminApiGet<ApiUsageMetricsResponse>("/admin/metrics/api"),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}


// ─── SA-G04: Geographic Intelligence ────────────────────────────────────

export interface GeoCountryMetrics {
  country_code: string;
  country_name: string;
  tenant_count: number;
  active_tenant_count: number;
  total_mrr_cents: number;
  currency_code: string;
  signup_trend: { month: string; count: number }[];
  top_plan: string | null;
}

export interface GeoIntelligenceResponse {
  countries: GeoCountryMetrics[];
  total_countries: number;
  primary_market: string;
}

export function useGeoIntelligence() {
  return useQuery({
    queryKey: ["admin", "geo-intelligence"],
    queryFn: () =>
      adminApiGet<GeoIntelligenceResponse>("/admin/analytics/geo"),
    staleTime: 5 * 60 * 1000,
  });
}
