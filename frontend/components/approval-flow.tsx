"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { SignaturePad } from "@/components/signature-pad";
import { PenLine } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ApprovalFlowProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  onApprove: (signatureBase64: string) => void;
  isLoading?: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ApprovalFlow({
  open,
  onOpenChange,
  title,
  description,
  onApprove,
  isLoading = false,
}: ApprovalFlowProps) {
  const [capturedSignature, setCapturedSignature] = useState<string | null>(
    null,
  );

  function handleSignature(base64Png: string) {
    setCapturedSignature(base64Png);
  }

  function handleClear() {
    setCapturedSignature(null);
  }

  function handleApprove() {
    if (!capturedSignature) return;
    onApprove(capturedSignature);
  }

  function handleClose(nextOpen: boolean) {
    if (!nextOpen) {
      // Reset captured signature when closing
      setCapturedSignature(null);
    }
    onOpenChange(nextOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <PenLine className="h-5 w-5 text-primary-600" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="py-2">
          {/* Signature instruction */}
          <p className="text-xs text-[hsl(var(--muted-foreground))] mb-3">
            Dibuje la firma del paciente en el área de abajo para confirmar su
            aprobación.
          </p>

          <SignaturePad
            onSignature={handleSignature}
            onClear={handleClear}
            height={160}
            disabled={isLoading}
          />

          {/* Captured confirmation indicator */}
          {capturedSignature && (
            <p className="mt-2 text-xs text-green-600 font-medium">
              Firma capturada. Presione "Aprobar y Firmar" para confirmar.
            </p>
          )}
        </div>

        <DialogFooter className="flex-col-reverse sm:flex-row gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => handleClose(false)}
            disabled={isLoading}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleApprove}
            disabled={isLoading || !capturedSignature}
            className="min-w-[150px]"
          >
            {isLoading ? "Procesando..." : "Aprobar y Firmar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
