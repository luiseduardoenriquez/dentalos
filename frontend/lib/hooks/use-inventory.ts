"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ItemCategory = "material" | "instrument" | "implant" | "medication";
export type ItemUnit = "units" | "ml" | "g" | "boxes";
export type ExpiryStatus = "ok" | "warning" | "critical" | "expired";
export type QuantityChangeReason =
  | "received"
  | "consumed"
  | "discarded"
  | "adjustment";

export interface InventoryItem {
  id: string;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  lot_number: string | null;
  expiry_date: string | null;
  expiry_status: string | null;
  manufacturer: string | null;
  supplier: string | null;
  cost_per_unit: number | null;
  minimum_stock: number;
  location: string | null;
  created_by: string;
  is_active: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface InventoryItemCreate {
  name: string;
  category: ItemCategory;
  quantity: number;
  unit: ItemUnit;
  lot_number?: string;
  expiry_date?: string;
  manufacturer?: string;
  supplier?: string;
  cost_per_unit?: number;
  minimum_stock?: number;
  location?: string;
}

export interface InventoryItemUpdate {
  name?: string;
  quantity_change?: number;
  change_reason?: QuantityChangeReason;
  change_notes?: string;
  lot_number?: string;
  expiry_date?: string;
  manufacturer?: string;
  supplier?: string;
  cost_per_unit?: number;
  minimum_stock?: number;
  location?: string;
}

export interface InventoryAlertItem {
  id: string;
  name: string;
  category: string;
  quantity: number;
  expiry_status: string | null;
  expiry_date: string | null;
  minimum_stock: number;
}

export interface InventoryAlerts {
  expired: InventoryAlertItem[];
  critical: InventoryAlertItem[];
  low_stock: InventoryAlertItem[];
}

export interface PaginatedItems {
  items: InventoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SterilizationRecord {
  id: string;
  autoclave_id: string;
  load_number: string;
  date: string;
  temperature_celsius: number | null;
  duration_minutes: number | null;
  biological_indicator: string | null;
  chemical_indicator: string | null;
  responsible_user_id: string;
  is_compliant: boolean;
  instrument_ids: string[];
  signature_data: string | null;
  signature_sha256_hash: string | null;
  notes: string | null;
  created_by: string;
  created_at: string;
}

export interface SterilizationRecordCreate {
  autoclave_id: string;
  load_number: string;
  date: string;
  temperature_celsius?: number;
  duration_minutes?: number;
  biological_indicator?: string;
  chemical_indicator?: string;
  responsible_user_id: string;
  is_compliant: boolean;
  instrument_ids?: string[];
  signature_data?: string;
  notes?: string;
}

export interface PaginatedSterilization {
  items: SterilizationRecord[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

const INVENTORY_KEYS = {
  all: ["inventory"] as const,
  items: (
    page: number,
    pageSize: number,
    category?: string,
    expiryStatus?: string,
    lowStock?: boolean,
  ) => ["inventory", "items", page, pageSize, category, expiryStatus, lowStock] as const,
  item: (id: string) => ["inventory", "item", id] as const,
  alerts: () => ["inventory", "alerts"] as const,
  sterilization: (page: number, pageSize: number) =>
    ["inventory", "sterilization", page, pageSize] as const,
  implants: (lotNumber?: string, patientId?: string) =>
    ["inventory", "implants", lotNumber, patientId] as const,
};

// ─── Hooks ────────────────────────────────────────────────────────────────────

/**
 * Fetch paginated inventory items with optional filters.
 */
export function useInventoryItems(
  page = 1,
  pageSize = 20,
  category?: string,
  expiryStatus?: string,
  lowStock?: boolean,
) {
  return useQuery<PaginatedItems>({
    queryKey: INVENTORY_KEYS.items(page, pageSize, category, expiryStatus, lowStock),
    queryFn: () =>
      apiGet<PaginatedItems>("/inventory/items", {
        page,
        page_size: pageSize,
        ...(category && { category }),
        ...(expiryStatus && { expiry_status: expiryStatus }),
        ...(lowStock !== undefined && { low_stock: lowStock }),
      }),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}

/**
 * Fetch a single inventory item by ID.
 */
export function useInventoryItem(itemId: string) {
  return useQuery<InventoryItem>({
    queryKey: INVENTORY_KEYS.item(itemId),
    queryFn: () => apiGet<InventoryItem>(`/inventory/items/${itemId}`),
    enabled: !!itemId,
  });
}

/**
 * Create a new inventory item.
 */
export function useCreateInventoryItem() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: InventoryItemCreate) =>
      apiPost<InventoryItem>("/inventory/items", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: INVENTORY_KEYS.all });
      toast({
        type: "success",
        duration: 5000,
        title: "Artículo creado",
        description: "El artículo fue agregado al inventario exitosamente.",
      });
    },
    onError: () => {
      toast({
        type: "error",
        duration: 5000,
        title: "Error al crear artículo",
        description: "No se pudo agregar el artículo. Intenta de nuevo.",
      });
    },
  });
}

/**
 * Update an existing inventory item (including stock adjustments).
 */
export function useUpdateInventoryItem(itemId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: InventoryItemUpdate) =>
      apiPut<InventoryItem>(`/inventory/items/${itemId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: INVENTORY_KEYS.all });
      toast({
        type: "success",
        duration: 5000,
        title: "Artículo actualizado",
        description: "Los cambios fueron guardados exitosamente.",
      });
    },
    onError: () => {
      toast({
        type: "error",
        duration: 5000,
        title: "Error al actualizar",
        description: "No se pudieron guardar los cambios. Intenta de nuevo.",
      });
    },
  });
}

/**
 * Fetch inventory alerts: expired, critical (expiry within 30 days), and low stock.
 */
export function useInventoryAlerts() {
  return useQuery<InventoryAlerts>({
    queryKey: INVENTORY_KEYS.alerts(),
    queryFn: () => apiGet<InventoryAlerts>("/inventory/alerts"),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Fetch paginated sterilization records.
 */
export function useSterilizationRecords(page = 1, pageSize = 20) {
  return useQuery<PaginatedSterilization>({
    queryKey: INVENTORY_KEYS.sterilization(page, pageSize),
    queryFn: () =>
      apiGet<PaginatedSterilization>("/inventory/sterilization", {
        page,
        page_size: pageSize,
      }),
  });
}

/**
 * Create a new sterilization record.
 */
export function useCreateSterilization() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: SterilizationRecordCreate) =>
      apiPost<SterilizationRecord>("/inventory/sterilization", data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["inventory", "sterilization"],
      });
      toast({
        type: "success",
        duration: 5000,
        title: "Registro creado",
        description: "El registro de esterilización fue guardado.",
      });
    },
    onError: () => {
      toast({
        type: "error",
        duration: 5000,
        title: "Error al guardar",
        description: "No se pudo crear el registro de esterilización.",
      });
    },
  });
}

/**
 * Search implants by lot number or patient ID for traceability.
 */
export function useImplantSearch(lotNumber?: string, patientId?: string) {
  return useQuery<InventoryItem[]>({
    queryKey: INVENTORY_KEYS.implants(lotNumber, patientId),
    queryFn: () =>
      apiGet<InventoryItem[]>("/inventory/implants/search", {
        ...(lotNumber && { lot_number: lotNumber }),
        ...(patientId && { patient_id: patientId }),
      }),
    enabled: !!(lotNumber || patientId),
    staleTime: 1000 * 60 * 5,
  });
}
