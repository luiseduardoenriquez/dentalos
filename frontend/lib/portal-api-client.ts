/**
 * Portal-specific Axios API client.
 *
 * Separate from the dashboard API client to avoid session conflicts.
 * Uses its own token storage and session cookie.
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

// ─── Portal Token Storage (in-memory) ───────────────────────────────────────

let portalAccessToken: string | null = null;

const PORTAL_SESSION_COOKIE = "dentalos_portal_session";

export function getPortalAccessToken(): string | null {
  return portalAccessToken;
}

export function setPortalAccessToken(token: string | null): void {
  portalAccessToken = token;
  if (typeof document !== "undefined") {
    if (token) {
      document.cookie = `${PORTAL_SESSION_COOKIE}=1; path=/; max-age=${30 * 86400}; samesite=strict`;
    }
  }
}

export function clearPortalAccessToken(): void {
  portalAccessToken = null;
  if (typeof document !== "undefined") {
    document.cookie = `${PORTAL_SESSION_COOKIE}=; path=/; max-age=0`;
  }
}

// ─── Axios Instance ─────────────────────────────────────────────────────────

const API_BASE_URL =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

export const portalApiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  withCredentials: true,
  timeout: 30_000,
});

// ─── Request Interceptor ────────────────────────────────────────────────────

portalApiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getPortalAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ─── Response Interceptor ───────────────────────────────────────────────────

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else if (token) resolve(token);
  });
  failedQueue = [];
}

portalApiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
    };

    const isUnauthorized = error.response?.status === 401;
    const isAlreadyRetried = originalRequest._retry;
    const isRefreshEndpoint = originalRequest.url?.includes("/portal/auth/refresh");

    if (!isUnauthorized || isAlreadyRetried || isRefreshEndpoint) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    if (isRefreshing) {
      return new Promise<unknown>((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            if (originalRequest.headers) {
              (originalRequest.headers as Record<string, string>)[
                "Authorization"
              ] = `Bearer ${token}`;
            }
            resolve(portalApiClient(originalRequest));
          },
          reject,
        });
      });
    }

    isRefreshing = true;

    try {
      const { data } = await portalApiClient.post<{
        access_token: string;
        token_type: string;
        expires_in: number;
      }>("/portal/auth/refresh", null);

      const newToken = data.access_token;
      setPortalAccessToken(newToken);
      processQueue(null, newToken);

      if (originalRequest.headers) {
        (originalRequest.headers as Record<string, string>)["Authorization"] =
          `Bearer ${newToken}`;
      }
      return portalApiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      clearPortalAccessToken();
      if (typeof window !== "undefined") {
        window.location.href = "/portal/login";
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

// ─── Typed Helpers ──────────────────────────────────────────────────────────

export async function portalApiGet<T>(
  url: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const { data } = await portalApiClient.get<T>(url, { params });
  return data;
}

export async function portalApiPost<T>(
  url: string,
  body?: unknown,
): Promise<T> {
  const { data } = await portalApiClient.post<T>(url, body);
  return data;
}
