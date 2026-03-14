"use client";

import { useEffect, useRef, useCallback } from "react";
import type { UseFormReturn, FieldValues } from "react-hook-form";
import { useToast } from "@/lib/hooks/use-toast";
import { saveDraft, getDraft, removeDraft } from "@/lib/db/offline-data-service";

// ─── Types ────────────────────────────────────────────────────────────────────

interface UseFormDraftOptions<T extends FieldValues> {
  /** Unique key for this form (e.g., "patient-create", "appointment-edit-{id}") */
  form_key: string;
  /** React Hook Form instance */
  form: UseFormReturn<T>;
  /** Debounce delay in ms before saving to storage (default: 2000) */
  debounce_ms?: number;
  /** Whether to show toast when draft is restored (default: true) */
  show_restore_toast?: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MAX_DRAFT_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Persists React Hook Form state to IndexedDB (via Dexie) with debounce.
 * Restores draft on mount. Clears on successful submit.
 * Supports rich text clinical content > 5MB (unlike localStorage).
 *
 * @example
 * const form = useForm<PatientCreate>();
 * const { clear_draft } = useFormDraft({ form_key: "patient-create", form });
 * // On submit success: clear_draft();
 */
export function useFormDraft<T extends FieldValues>({
  form_key,
  form,
  debounce_ms = 2_000,
  show_restore_toast = true,
}: UseFormDraftOptions<T>) {
  const { info } = useToast();
  const timer_ref = useRef<ReturnType<typeof setTimeout> | null>(null);
  const restored_ref = useRef(false);

  // Restore draft on mount (once)
  useEffect(() => {
    if (restored_ref.current) return;
    restored_ref.current = true;

    (async () => {
      try {
        const draft = await getDraft(form_key);
        if (!draft) return;

        // Skip expired drafts
        if (Date.now() - draft.saved_at > MAX_DRAFT_AGE_MS) {
          removeDraft(form_key).catch(() => {});
          return;
        }

        // Restore form values
        form.reset(draft.data as T, { keepDefaultValues: true });

        if (show_restore_toast) {
          const ago = formatTimeAgo(draft.saved_at);
          info("Borrador restaurado", `Se recupero un borrador guardado ${ago}.`);
        }
      } catch {
        // Corrupted draft — remove it
        removeDraft(form_key).catch(() => {});
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-save on form changes (debounced)
  useEffect(() => {
    const subscription = form.watch((values) => {
      if (timer_ref.current) clearTimeout(timer_ref.current);

      timer_ref.current = setTimeout(() => {
        saveDraft(form_key, values).catch(() => {
          // IDB write failure — silent fail
        });
      }, debounce_ms);
    });

    return () => {
      subscription.unsubscribe();
      if (timer_ref.current) clearTimeout(timer_ref.current);
    };
  }, [form, form_key, debounce_ms]);

  // Clear draft (call on successful submit)
  const clear_draft = useCallback(() => {
    removeDraft(form_key).catch(() => {});
    if (timer_ref.current) clearTimeout(timer_ref.current);
  }, [form_key]);

  return { clear_draft };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTimeAgo(timestamp: number): string {
  const diff_ms = Date.now() - timestamp;
  const minutes = Math.floor(diff_ms / 60_000);
  if (minutes < 1) return "hace menos de 1 min";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return `hace ${Math.floor(hours / 24)} d`;
}
