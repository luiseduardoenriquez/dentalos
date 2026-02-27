/**
 * Axios API client for the DentalOS admin panel.
 *
 * DIFFERENCES from lib/api-client.ts:
 * - Uses the admin token from getAdminToken() — never the clinic access token.
 * - On 401: redirects to /admin/login and clears admin auth. No token refresh.
 * - withCredentials is false — admin has no HttpOnly refresh cookie. Sessions
 *   are fixed at 1 hour and require re-login on expiry.
 * - All admin endpoints are under /api/v1/admin/... — same base URL as the
 *   clinic API, different path namespace enforced at the backend RBAC level.
 *
 * SECURITY: This module must never import from lib/auth.ts or share state with
 * lib/api-client.ts. The two clients are intentionally isolated.
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";
import { clearAdminToken, getAdminToken } from "./hooks/use-admin-auth";

// ─── Types ─────────────────────────────────────────────────────────────────────

interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

// ─── Axios Instance ─────────────────────────────────────────────────────────────

const API_BASE_URL =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

export const adminApiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  // Admin sessions use Bearer token only — no HttpOnly cookie involved.
  withCredentials: false,
  timeout: 30_000,
});

// ─── Request Interceptor ──────────────────────────────────────────────────────

adminApiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAdminToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ─── Response Interceptor ─────────────────────────────────────────────────────

adminApiClient.interceptors.response.use(
  // Pass-through successful responses
  (response) => response,

  async (error: AxiosError<ApiError>) => {
    const isUnauthorized = error.response?.status === 401;

    if (isUnauthorized) {
      // Admin sessions cannot be silently refreshed — clear state and force re-login.
      clearAdminToken();

      // Import dynamically to avoid circular dependency at module init time.
      // The store's clear_admin_auth is called here so any currently mounted
      // components that read is_authenticated will immediately re-render.
      const { useAdminAuthStore } = await import("./hooks/use-admin-auth");
      useAdminAuthStore.getState().clear_admin_auth();

      if (typeof window !== "undefined") {
        window.location.href = "/admin/login";
      }
    }

    return Promise.reject(error);
  },
);

// ─── Typed Request Helpers ─────────────────────────────────────────────────────

/**
 * Typed GET request via the admin Axios client.
 * Returns the response data directly (unwraps the Axios wrapper).
 *
 * @param url - Path relative to /api/v1 (e.g. "/admin/tenants")
 * @param params - Optional query parameters
 */
export async function adminApiGet<T>(
  url: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const { data } = await adminApiClient.get<T>(url, { params });
  return data;
}

/**
 * Typed POST request via the admin Axios client.
 *
 * @param url - Path relative to /api/v1
 * @param body - Request body (will be JSON-serialised)
 */
export async function adminApiPost<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await adminApiClient.post<T>(url, body);
  return data;
}

/**
 * Typed PUT request via the admin Axios client.
 *
 * @param url - Path relative to /api/v1
 * @param body - Request body (will be JSON-serialised)
 */
export async function adminApiPut<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await adminApiClient.put<T>(url, body);
  return data;
}

export type { ApiError as AdminApiError };
