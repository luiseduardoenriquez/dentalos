"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface PlatformAnnouncement {
  id: string;
  title: string;
  body: string;
  announcement_type: "info" | "warning" | "critical";
  visibility: string;
  is_dismissable: boolean;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
}

/**
 * Fetch active platform announcements for the current clinic context.
 * Used by the clinic dashboard to show admin-published banners.
 */
export function useActiveAnnouncements() {
  return useQuery<PlatformAnnouncement[]>({
    queryKey: ["announcements", "active"],
    queryFn: async () => {
      const { data } = await apiClient.get("/announcements/active");
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}
