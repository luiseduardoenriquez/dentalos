"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useUpdateCallNotes } from "@/lib/hooks/use-calls";

// ─── Props ────────────────────────────────────────────────────────────────────

interface CallNotesDialogProps {
  callId: string;
  currentNotes: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Modal dialog for editing the notes on a call log entry.
 *
 * Uses useUpdateCallNotes mutation and closes automatically on success.
 */
export function CallNotesDialog({
  callId,
  currentNotes,
  open,
  onOpenChange,
}: CallNotesDialogProps) {
  const [notes, setNotes] = React.useState(currentNotes);

  const { mutate: updateNotes, isPending } = useUpdateCallNotes(callId);

  // Sync textarea when currentNotes prop changes (e.g., dialog reopened for a different call)
  React.useEffect(() => {
    setNotes(currentNotes);
  }, [currentNotes, open]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    updateNotes(
      { notes: notes.trim() },
      {
        onSuccess: () => {
          onOpenChange(false);
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Notas de la llamada</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="call-notes">
              Notas
            </Label>
            <Textarea
              id="call-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Escribe aquí las notas de la llamada..."
              rows={5}
              className="resize-none"
              disabled={isPending}
            />
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Guardando..." : "Guardar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
