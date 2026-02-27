"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CountryConfig {
  country_code: string;
  country_name: string;
  procedure_code_system: string;
  document_types: Array<{ code: string; label: string }>;
  code_systems: Record<string, unknown>;
  retention_rules: Record<string, unknown>;
  regulatory_references: Array<{
    code: string;
    title: string;
    topic: string;
    deadline: string | null;
  }>;
  feature_flags: Record<string, unknown>;
}

export interface RDAGap {
  field_name: string;
  module: string;
  severity: string;
  weight: number;
  current_count: number;
  expected_count: number;
  gap_percentage: number;
  corrective_action: string;
}

export interface RDAModuleBreakdown {
  module: string;
  label: string;
  total_fields: number;
  compliant_fields: number;
  compliance_percentage: number;
  gaps: RDAGap[];
}

export interface RDAStatus {
  overall_compliance_percentage: number;
  compliance_level: string;
  deadline: string;
  modules: RDAModuleBreakdown[];
  gaps: RDAGap[];
  total_records_analyzed: number;
  last_computed_at: string | null;
  cached: boolean;
}

export interface RIPSBatchFile {
  file_type: string;
  storage_path: string | null;
  download_url: string | null;
  size_bytes: number;
  record_count: number;
}

export interface RIPSBatchError {
  severity: string;
  rule_code: string;
  message: string;
  record_ref: string | null;
  field_name: string | null;
}

export interface RIPSBatch {
  id: string;
  period_start: string;
  period_end: string;
  status: string;
  file_types: string[];
  files: RIPSBatchFile[];
  errors: RIPSBatchError[];
  error_count: number;
  warning_count: number;
  created_at: string;
  generated_at: string | null;
  validated_at: string | null;
  failure_reason: string | null;
}

export interface RIPSBatchList {
  items: RIPSBatch[];
  total: number;
  page: number;
  page_size: number;
}

export interface EInvoiceStatus {
  id: string;
  invoice_id: string;
  status: string;
  cufe: string | null;
  matias_submission_id: string | null;
  dian_environment: string;
  xml_url: string | null;
  pdf_url: string | null;
  retry_count: number;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useCountryConfig() {
  return useQuery<CountryConfig>({
    queryKey: ["compliance", "config"],
    queryFn: () => apiGet<CountryConfig>("/compliance/config"),
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

export function useRDAStatus(refresh = false) {
  return useQuery<RDAStatus>({
    queryKey: ["compliance", "rda", "status", refresh],
    queryFn: () =>
      apiGet<RDAStatus>("/compliance/rda/status", { refresh }),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useRIPSBatches(page = 1, pageSize = 20) {
  return useQuery<RIPSBatchList>({
    queryKey: ["compliance", "rips", "batches", page, pageSize],
    queryFn: () =>
      apiGet<RIPSBatchList>("/compliance/rips", {
        page,
        page_size: pageSize,
      }),
  });
}

export function useRIPSBatch(batchId: string) {
  return useQuery<RIPSBatch>({
    queryKey: ["compliance", "rips", "batch", batchId],
    queryFn: () => apiGet<RIPSBatch>(`/compliance/rips/${batchId}`),
    enabled: !!batchId,
  });
}

export function useGenerateRIPS() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: {
      period_start: string;
      period_end: string;
      file_types?: string[];
    }) => apiPost<RIPSBatch>("/compliance/rips/generate", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance", "rips"] });
      toast({
        type: "success",
        duration: 5000,
        title: "RIPS en generación",
        description: "El lote RIPS se está generando. Actualiza la página para ver el progreso.",
      });
    },
    onError: () => {
      toast({
        type: "error",
        duration: 5000,
        title: "Error",
        description: "No se pudo iniciar la generación de RIPS.",
      });
    },
  });
}

export function useValidateRIPS() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (batchId: string) =>
      apiPost<unknown>(`/compliance/rips/${batchId}/validate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance", "rips"] });
      toast({
        type: "success",
        duration: 5000,
        title: "Validación iniciada",
        description: "El lote RIPS se está validando.",
      });
    },
    onError: () => {
      toast({
        type: "error",
        duration: 5000,
        title: "Error",
        description: "No se pudo iniciar la validación.",
      });
    },
  });
}

export function useCreateEInvoice() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (invoiceId: string) =>
      apiPost<EInvoiceStatus>("/compliance/e-invoice", {
        invoice_id: invoiceId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance", "einvoice"] });
      toast({
        type: "success",
        duration: 5000,
        title: "Factura electrónica enviada",
        description: "La factura se está procesando ante la DIAN.",
      });
    },
    onError: () => {
      toast({
        type: "error",
        duration: 5000,
        title: "Error",
        description: "No se pudo enviar la factura electrónica.",
      });
    },
  });
}

export function useEInvoiceStatus(einvoiceId: string) {
  return useQuery<EInvoiceStatus>({
    queryKey: ["compliance", "einvoice", einvoiceId],
    queryFn: () =>
      apiGet<EInvoiceStatus>(`/compliance/e-invoice/${einvoiceId}/status`),
    enabled: !!einvoiceId,
    refetchInterval: 10_000, // Poll every 10s for in-flight submissions
  });
}
