"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient, apiGet } from "@/lib/api-client";
import { useToast } from "@/lib/hooks/use-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PatientImportJob {
  job_id: string;
  /** "queued" | "processing" | "completed" | "failed" */
  status: string;
  total_rows: number;
  processed_rows: number;
  success_count: number;
  error_count: number;
  duplicate_count: number;
  error_file_url: string | null;
  created_at: string;
}

export interface ImportStartResponse {
  job_id: string;
  status: string;
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

/**
 * Mutation to start a patient CSV import.
 * Uploads the file as multipart/form-data to POST /patients/import.
 * Returns 202 with { job_id, status }.
 *
 * @example
 * const { mutate: startImport, isPending } = useStartImport();
 * startImport(file, { onSuccess: (resp) => setJobId(resp.job_id) });
 */
export function useStartImport() {
  const { success, error } = useToast();

  return useMutation({
    mutationFn: async (file: File): Promise<ImportStartResponse> => {
      const formData = new FormData();
      formData.append("file", file);

      const { data } = await apiClient.post<ImportStartResponse>(
        "/patients/import",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );
      return data;
    },
    onSuccess: () => {
      success("Importación iniciada", "El archivo se está procesando en segundo plano.");
    },
    onError: () => {
      error("Error al iniciar importación", "No se pudo iniciar la importación. Verifica el archivo e inténtalo de nuevo.");
    },
  });
}

/**
 * Query to poll the status of an import job.
 * Polls every 3 seconds while status is "queued" or "processing".
 * Stops polling once status is "completed" or "failed".
 *
 * @param jobId - The job_id returned by useStartImport
 *
 * @example
 * const { data: job } = useImportStatus(jobId);
 */
export function useImportStatus(jobId: string) {
  return useQuery<PatientImportJob>({
    queryKey: ["patients", "import", jobId],
    queryFn: () => apiGet<PatientImportJob>(`/patients/import/${jobId}`),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 3000;
    },
  });
}
