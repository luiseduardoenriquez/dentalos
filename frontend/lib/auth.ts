/**
 * In-memory access token storage.
 *
 * SECURITY NOTE: Access tokens are stored in a module-level JS variable
 * (NOT localStorage, NOT sessionStorage) per the DentalOS security spec.
 * This prevents XSS attacks from reading the token via document.cookie or
 * Storage APIs. The token lives only in the JS heap and is cleared on page
 * reload, which is intentional — the refresh token (HttpOnly cookie) is used
 * to rehydrate the access token transparently via /auth/refresh.
 *
 * Refresh tokens are HttpOnly cookies set by the backend. This module has
 * no visibility into them; the browser sends them automatically.
 */

// Module-level variable — NEVER stored in localStorage per security spec.
let accessToken: string | null = null;

/**
 * Returns the current access token, or null if not authenticated.
 */
export function getAccessToken(): string | null {
  return accessToken;
}

/**
 * Session indicator cookie name — used by Next.js middleware to decide
 * whether to redirect to /login. This is NOT a security token; the real
 * auth check happens via the JWT in the Authorization header.
 */
const SESSION_COOKIE = "dentalos_session";

/**
 * Stores a new access token in memory.
 * Called after a successful login or token refresh.
 * Also sets a session indicator cookie so the Next.js middleware
 * can gate dashboard routes without seeing the HttpOnly refresh cookie.
 *
 * @param token - JWT access token string
 */
export function setAccessToken(token: string | null): void {
  accessToken = token;
  if (typeof document !== "undefined") {
    if (token) {
      // Set a session indicator cookie (same-site, 30 days, NOT HttpOnly)
      document.cookie = `${SESSION_COOKIE}=1; path=/; max-age=${30 * 86400}; samesite=strict`;
    }
  }
}

/**
 * Clears the in-memory access token.
 * Called on logout or when refresh fails (forces re-login).
 */
export function clearAccessToken(): void {
  accessToken = null;
  if (typeof document !== "undefined") {
    document.cookie = `${SESSION_COOKIE}=; path=/; max-age=0`;
  }
}

/**
 * Returns true if there is an access token currently stored in memory.
 * Note: this does NOT validate the token signature or expiry — that
 * validation happens server-side.
 */
export function isTokenPresent(): boolean {
  return accessToken !== null;
}
