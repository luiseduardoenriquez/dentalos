/**
 * Axios API client for DentalOS backend.
 *
 * Features:
 * - Base URL from NEXT_PUBLIC_API_URL env var
 * - Injects Authorization Bearer token from in-memory store on every request
 * - Automatic token refresh on 401 responses (silent refresh via HttpOnly cookie)
 * - Queues concurrent 401 responses during refresh to avoid multiple refresh calls
 * - Clears auth state and redirects to /login when refresh fails
 * - withCredentials: true so the browser sends the HttpOnly refresh cookie
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";
import { clearAccessToken, getAccessToken, setAccessToken } from "./auth";
import { getApiBaseUrl } from "./api-base-url";

// ─── Types ────────────────────────────────────────────────────────────────────

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

// ─── Axios Instance ───────────────────────────────────────────────────────────

const API_BASE_URL = getApiBaseUrl();

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  // Required so the browser sends the HttpOnly refresh token cookie automatically
  withCredentials: true,
  timeout: 30_000,
});

// ─── Refresh Token State ──────────────────────────────────────────────────────

/** Whether a token refresh is currently in-flight */
let isRefreshing = false;

/**
 * Queue of resolve/reject callbacks waiting for the refresh to complete.
 * All 401 responses that arrive while a refresh is in-flight are added here
 * so we only call /auth/refresh once, not N times.
 */
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else if (token) {
      resolve(token);
    }
  });
  failedQueue = [];
}

// ─── Request Interceptor ──────────────────────────────────────────────────────

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ─── Response Interceptor ─────────────────────────────────────────────────────

apiClient.interceptors.response.use(
  // Pass-through for successful responses
  (response) => response,

  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Only attempt refresh on 401 errors that haven't already been retried
    // and are not themselves the refresh endpoint (prevents infinite loop)
    const isUnauthorized = error.response?.status === 401;
    const isAlreadyRetried = originalRequest._retry;
    const isRefreshEndpoint = originalRequest.url?.includes("/auth/refresh-token");

    if (!isUnauthorized || isAlreadyRetried || isRefreshEndpoint) {
      return Promise.reject(error);
    }

    // Mark this request as retried so we don't loop
    originalRequest._retry = true;

    if (isRefreshing) {
      // A refresh is already in-flight — queue this request and wait
      return new Promise<unknown>((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            if (originalRequest.headers) {
              (originalRequest.headers as Record<string, string>)["Authorization"] =
                `Bearer ${token}`;
            }
            resolve(apiClient(originalRequest));
          },
          reject,
        });
      });
    }

    isRefreshing = true;

    try {
      // Attempt silent refresh using the HttpOnly cookie (sent automatically via withCredentials)
      const { data } = await apiClient.post<TokenResponse>("/auth/refresh-token", null, {
        // Explicitly bypass the interceptor for the refresh call itself
        withCredentials: true,
      });

      const newToken = data.access_token;
      setAccessToken(newToken);

      // Retry all queued requests with the new token
      processQueue(null, newToken);

      // Retry the original request
      if (originalRequest.headers) {
        (originalRequest.headers as Record<string, string>)["Authorization"] = `Bearer ${newToken}`;
      }
      return apiClient(originalRequest);
    } catch (refreshError) {
      // Refresh failed — clear auth state and redirect to login
      processQueue(refreshError, null);
      clearAccessToken();

      // Redirect to login only in browser context
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }

      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

// ─── Network Retry Interceptor ───────────────────────────────────────────────

const MAX_RETRIES = 3;
const RETRY_DELAY_BASE = 1_000; // 1s, 2s, 4s exponential backoff

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as AxiosRequestConfig & { _retryCount?: number };
    if (!config) return Promise.reject(error);

    // Only retry on network errors (no response = connection failure)
    // Do NOT retry if there is an HTTP response (even 5xx) — let the caller handle it
    if (error.response) return Promise.reject(error);

    // Do not retry auth endpoints (refresh is handled separately)
    if (config.url?.includes("/auth/")) return Promise.reject(error);

    const retryCount = config._retryCount ?? 0;
    if (retryCount >= MAX_RETRIES) return Promise.reject(error);

    config._retryCount = retryCount + 1;
    const delay = RETRY_DELAY_BASE * 2 ** retryCount;
    await new Promise((resolve) => setTimeout(resolve, delay));
    return apiClient(config);
  },
);

// ─── Typed Request Helpers ────────────────────────────────────────────────────

/**
 * Typed GET request helper.
 * Returns the response data directly (unwraps axios wrapper).
 */
export async function apiGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const { data } = await apiClient.get<T>(url, { params });
  return data;
}

/**
 * Typed POST request helper.
 */
export async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await apiClient.post<T>(url, body);
  return data;
}

/**
 * Typed PUT request helper.
 */
export async function apiPut<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await apiClient.put<T>(url, body);
  return data;
}

/**
 * Typed DELETE request helper.
 */
export async function apiDelete<T>(url: string): Promise<T> {
  const { data } = await apiClient.delete<T>(url);
  return data;
}

export type { ApiError };
