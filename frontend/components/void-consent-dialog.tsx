"use client";

import * as React from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface VoidConsentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onVoid: (reason: string) => void;
  isLoading?: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const REASON_MIN_LENGTH = 20;
const REASON_MAX_LENGTH = 1000;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Confirmation dialog for voiding a consent document.
 * Requires the user to provide a reason (20–1000 chars) before proceeding.
 * This action is irreversible and must be clearly communicated.
 */
function VoidConsentDialog({
  open,
  onOpenChange,
  onVoid,
  isLoading = false,
}: VoidConsentDialogProps) {
  const [reason, setReason] = React.useState("");

  const char_count = reason.length;
  const is_too_short = char_count < REASON_MIN_LENGTH;
  const is_too_long = char_count > REASON_MAX_LENGTH;
  const is_valid = !is_too_short && !is_too_long;

  // Reset reason when dialog closes
  React.useEffect(() => {
    if (!open) {
      setReason("");
    }
  }, [open]);

  function handle_submit() {
    if (!is_valid) return;
    onVoid(reason.trim());
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-1">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive-100 dark:bg-destructive-900/30">
              <AlertTriangle className="h-5 w-5 text-destructive-600 dark:text-destructive-400" />
            </div>
            <DialogTitle>Anular consentimiento</DialogTitle>
          </div>
          <DialogDescription className="text-sm text-[hsl(var(--muted-foreground))]">
            Esta acción es{" "}
            <span className="font-semibold text-foreground">irreversible</span>. El
            consentimiento quedará marcado como anulado y no podrá ser firmado ni modificado.
            Se guardará un registro de auditoría con la razón de anulación.
          </DialogDescription>
        </DialogHeader>

        {/* ─── Reason Textarea ──────────────────────────────────── */}
        <div className="space-y-2 py-2">
          <label
            htmlFor="void-reason"
            className="text-sm font-medium text-foreground"
          >
            Motivo de anulación{" "}
            <span className="text-destructive-600">*</span>
          </label>
          <textarea
            id="void-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Describe el motivo por el que se anula este consentimiento..."
            rows={4}
            maxLength={REASON_MAX_LENGTH}
            disabled={isLoading}
            className={cn(
              "w-full resize-none rounded-md border px-3 py-2",
              "text-sm text-foreground placeholder:text-[hsl(var(--muted-foreground))]",
              "bg-[hsl(var(--background))]",
              "focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-2",
              "disabled:cursor-not-allowed disabled:opacity-50",
              "transition-colors",
              is_too_long
                ? "border-destructive-500 focus:ring-destructive-500"
                : "border-[hsl(var(--border))]",
            )}
          />

          {/* ─── Character Counter ──────────────────────────────── */}
          <div className="flex items-center justify-between text-xs">
            <span
              className={cn(
                "transition-colors",
                is_too_short && char_count > 0
                  ? "text-warning-600 dark:text-warning-400"
                  : is_too_long
                    ? "text-destructive-600 dark:text-destructive-400"
                    : "text-[hsl(var(--muted-foreground))]",
              )}
            >
              {is_too_short && char_count > 0 && (
                <>Mínimo {REASON_MIN_LENGTH} caracteres ({REASON_MIN_LENGTH - char_count} restantes)</>
              )}
              {char_count === 0 && (
                <>Mínimo {REASON_MIN_LENGTH} caracteres requeridos</>
              )}
              {is_valid && <>Descripción válida</>}
              {is_too_long && <>Máximo {REASON_MAX_LENGTH} caracteres</>}
            </span>
            <span
              className={cn(
                "font-medium tabular-nums",
                is_too_long
                  ? "text-destructive-600 dark:text-destructive-400"
                  : "text-[hsl(var(--muted-foreground))]",
              )}
            >
              {char_count} / {REASON_MAX_LENGTH}
            </span>
          </div>
        </div>

        {/* ─── Actions ──────────────────────────────────────────── */}
        <DialogFooter className="flex-col-reverse sm:flex-row gap-2 pt-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancelar
          </Button>
          <Button
            variant="destructive"
            onClick={handle_submit}
            disabled={!is_valid || isLoading}
          >
            {isLoading ? "Anulando..." : "Anular Consentimiento"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

VoidConsentDialog.displayName = "VoidConsentDialog";

export { VoidConsentDialog };
