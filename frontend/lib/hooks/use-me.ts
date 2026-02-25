"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api-client";
import { useAuthStore, type MeResponse } from "@/lib/hooks/use-auth";

// ─── Query Key ────────────────────────────────────────────────────────────────

export const ME_QUERY_KEY = ["auth", "me"] as const;

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Query hook for GET /auth/me.
 *
 * Used in the dashboard layout to:
 * 1. Rehydrate the auth store after a page reload (access token lost from memory,
 *    but the HttpOnly refresh cookie is sent automatically → interceptor gets new token).
 * 2. Keep user/tenant data fresh without requiring a full re-login.
 *
 * On success: hydrates the Zustand auth store with current user + tenant context.
 * On 401 error: clears auth state and redirects to /login.
 *
 * The auth store's is_loading flag is managed here so layouts can show a
 * full-page skeleton while the check is in flight.
 *
 * @example
 * // In the dashboard layout:
 * const { isLoading } = useMe();
 * if (isLoading) return <FullPageSkeleton />;
 */
export function useMe() {
  const router = useRouter();
  const { set_auth, set_loading, clear_auth } = useAuthStore();

  const query = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: () => apiGet<MeResponse>("/auth/me"),
    // Only try once — if the refresh cookie is gone, we redirect immediately
    retry: false,
    // Stale time matches Redis session TTL (15 min)
    staleTime: 15 * 60 * 1000,
  });

  // Hydrate the store when data arrives
  useEffect(() => {
    if (query.data) {
      set_auth(query.data);
    }
  }, [query.data, set_auth]);

  // Redirect to login on any auth error (401 handled by interceptor, but
  // we also guard here for network errors or unexpected 403s)
  useEffect(() => {
    if (query.isError) {
      clear_auth();
      router.replace("/login");
    }
  }, [query.isError, clear_auth, router]);

  // Sync the Zustand is_loading flag
  useEffect(() => {
    set_loading(query.isLoading);
  }, [query.isLoading, set_loading]);

  return {
    isLoading: query.isLoading,
    isError: query.isError,
    data: query.data,
  };
}
