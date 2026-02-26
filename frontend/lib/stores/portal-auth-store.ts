"use client";

import { create } from "zustand";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PortalPatient {
  id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
}

export interface PortalTenant {
  slug: string;
  name: string;
  logo_url: string | null;
  primary_color: string | null;
}

// ─── Store ────────────────────────────────────────────────────────────────────

interface PortalAuthState {
  patient: PortalPatient | null;
  tenant: PortalTenant | null;
  is_loading: boolean;
  is_authenticated: boolean;

  set_portal_auth: (patient: PortalPatient, tenant?: PortalTenant | null) => void;
  clear_portal_auth: () => void;
  set_loading: (loading: boolean) => void;
}

/**
 * Portal auth store — separate from the dashboard auth store.
 * Portal patients have their own session cookie and token flow.
 */
export const usePortalAuthStore = create<PortalAuthState>((set) => ({
  patient: null,
  tenant: null,
  is_loading: true,
  is_authenticated: false,

  set_portal_auth: (patient: PortalPatient, tenant?: PortalTenant | null) => {
    set({
      patient,
      tenant: tenant ?? null,
      is_authenticated: true,
      is_loading: false,
    });
  },

  clear_portal_auth: () => {
    set({
      patient: null,
      tenant: null,
      is_authenticated: false,
      is_loading: false,
    });
    // Clear portal session cookie
    if (typeof document !== "undefined") {
      document.cookie = "dentalos_portal_session=; path=/; max-age=0";
    }
  },

  set_loading: (loading: boolean) => {
    set({ is_loading: loading });
  },
}));
