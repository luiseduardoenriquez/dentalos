import {
  queueMutation,
  getPendingMutations,
  getPendingCount,
  removePendingMutation,
  clearPendingMutations,
} from "@/lib/db/offline-data-service";
import type { PendingSyncItem } from "@/lib/db/offline-db";
import { apiClient } from "@/lib/api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface QueuedMutationInput {
  method: "POST" | "PUT" | "DELETE";
  url: string;
  body?: unknown;
  resource: string;
  resource_id?: string | null;
}

export interface ProcessResult {
  total: number;
  succeeded: number;
  failed: number;
  conflicts: number;
}

// ─── Queue Operations ─────────────────────────────────────────────────────────

/**
 * Queue a failed mutation for later sync.
 * Called when an API mutation fails due to network error.
 */
export async function queueOfflineMutation(input: QueuedMutationInput): Promise<number> {
  return queueMutation({
    method: input.method,
    url: input.url,
    body: input.body ?? null,
    resource: input.resource,
    resource_id: input.resource_id ?? null,
    queued_at: Date.now(),
    retry_count: 0,
  });
}

export { getPendingMutations, getPendingCount };

/**
 * Process all pending mutations against the API.
 * Returns a summary of results.
 */
export async function processPendingQueue(): Promise<ProcessResult> {
  const pending = await getPendingMutations();
  const result: ProcessResult = {
    total: pending.length,
    succeeded: 0,
    failed: 0,
    conflicts: 0,
  };

  for (const item of pending) {
    try {
      const response = await apiClient.request({
        method: item.method,
        url: item.url,
        data: item.body,
      });

      if (response.status >= 200 && response.status < 300) {
        result.succeeded++;
        await removePendingMutation(item.id!);
      } else if (response.status === 409) {
        result.conflicts++;
        await removePendingMutation(item.id!);
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status && status >= 400 && status < 500) {
        // Client error — don't retry
        result.failed++;
        await removePendingMutation(item.id!);
      } else {
        // Network error — leave for next try
        result.failed++;
      }
    }
  }

  return result;
}

/**
 * Discard a specific pending mutation.
 */
export async function discardPendingMutation(id: number): Promise<void> {
  await removePendingMutation(id);
}

/**
 * Discard all pending mutations.
 */
export async function discardAllPending(): Promise<void> {
  await clearPendingMutations();
}
