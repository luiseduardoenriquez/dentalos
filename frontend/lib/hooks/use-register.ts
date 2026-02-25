"use client";

import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import { setAccessToken } from "@/lib/auth";
import { useAuthStore, type MeResponse } from "@/lib/hooks/use-auth";
import type { RegisterFormValues } from "@/lib/validations/auth";

// ─── Response Type ─────────────────────────────────────────────────────────────

/**
 * Response from POST /auth/register.
 * Returns a tenant-scoped access token and the full /auth/me context.
 */
export interface RegisterResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  me: MeResponse;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Mutation hook for POST /auth/register.
 *
 * Registers a new clinic owner and creates their tenant in one step.
 * On success:
 *   - Stores the access token in memory.
 *   - Hydrates the auth store with user + tenant data.
 *
 * After success the caller should redirect to /onboarding.
 *
 * @example
 * const { mutate: register, isPending } = useRegister();
 * register({ name, email, password, clinic_name, country });
 */
export function useRegister() {
  const set_auth = useAuthStore((s) => s.set_auth);

  return useMutation({
    mutationFn: (payload: RegisterFormValues) =>
      apiPost<RegisterResponse>("/auth/register", payload),

    onSuccess: (data) => {
      setAccessToken(data.access_token);
      set_auth(data.me);
    },
  });
}
