"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { buildQueryString } from "@/lib/utils";

export interface ServiceCatalogItem {
  id: string;
  name: string;
  cups_code: string | null;
  description: string | null;
  default_price: number; // cents
  category: string | null;
  is_active: boolean;
}

export interface ServiceCatalogResponse {
  items: ServiceCatalogItem[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Search the service catalog for autocomplete in invoice line items.
 * Only fetches when search term is at least 2 characters.
 */
export function useServiceCatalog(search: string, enabled = true) {
  const queryParams: Record<string, unknown> = {
    search,
    page: 1,
    page_size: 10,
  };

  return useQuery({
    queryKey: ["service-catalog", search],
    queryFn: () =>
      apiGet<ServiceCatalogResponse>(
        `/billing/services${buildQueryString(queryParams)}`,
      ),
    enabled: enabled && search.length >= 2,
    staleTime: 60_000,
    placeholderData: (previousData) => previousData,
  });
}
