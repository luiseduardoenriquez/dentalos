"use client";

import * as React from "react";
import { Phone, X, UserCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { IncomingCallSSEEvent } from "@/lib/hooks/use-calls-sse";

// ─── Constants ────────────────────────────────────────────────────────────────

const AUTO_DISMISS_MS = 30_000;

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Masks a phone number, showing only the last 4 digits.
 * e.g. "+573001234567" → "***4567"
 */
function maskPhoneNumber(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length <= 4) return phone;
  const last4 = digits.slice(-4);
  return `***${last4}`;
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface IncomingCallPopupProps {
  call: IncomingCallSSEEvent | null;
  onOpen: () => void;
  onDismiss: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Floating notification popup for incoming VoIP calls.
 *
 * - Appears at the bottom-right corner of the viewport
 * - Shows masked phone number and matched patient name (if any)
 * - Auto-dismisses after 30 seconds
 * - Provides "Abrir ficha" and "Descartar" actions
 */
export function IncomingCallPopup({
  call,
  onOpen,
  onDismiss,
}: IncomingCallPopupProps) {
  // Auto-dismiss after 30 seconds
  React.useEffect(() => {
    if (!call) return;
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [call, onDismiss]);

  if (!call) return null;

  return (
    <div
      className={cn(
        "fixed bottom-6 right-6 z-50 w-80",
        "animate-in slide-in-from-bottom-4 fade-in-0 duration-300",
      )}
      role="alertdialog"
      aria-labelledby="incoming-call-title"
      aria-describedby="incoming-call-desc"
    >
      <Card className="shadow-lg border-primary-200 dark:border-primary-800">
        <CardContent className="p-4">
          {/* Header */}
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              {/* Pulsing ring icon */}
              <div className="relative shrink-0">
                <span className="absolute inset-0 rounded-full bg-primary-500/30 animate-ping" />
                <div className="relative flex h-9 w-9 items-center justify-center rounded-full bg-primary-600 text-white">
                  <Phone className="h-4 w-4" />
                </div>
              </div>
              <div>
                <p
                  id="incoming-call-title"
                  className="text-sm font-semibold text-foreground"
                >
                  Llamada entrante
                </p>
                <p
                  id="incoming-call-desc"
                  className="text-xs text-[hsl(var(--muted-foreground))] tabular-nums"
                >
                  {maskPhoneNumber(call.phone_number)}
                </p>
              </div>
            </div>

            {/* Close button */}
            <button
              type="button"
              onClick={onDismiss}
              className="shrink-0 rounded-md p-1 text-[hsl(var(--muted-foreground))] hover:text-foreground hover:bg-[hsl(var(--muted))] transition-colors"
              aria-label="Cerrar notificación"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Patient info (if matched) */}
          {call.patient_name && (
            <div className="flex items-center gap-2 mb-3 rounded-md bg-[hsl(var(--muted))] px-3 py-2">
              <UserCircle className="h-4 w-4 shrink-0 text-[hsl(var(--muted-foreground))]" />
              <p className="text-sm font-medium text-foreground truncate">
                {call.patient_name}
              </p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2">
            <Button
              size="sm"
              className="flex-1"
              onClick={onOpen}
              aria-label="Abrir ficha del paciente"
            >
              <Phone className="mr-1.5 h-3.5 w-3.5" />
              Abrir ficha
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="flex-1"
              onClick={onDismiss}
              aria-label="Descartar llamada"
            >
              Descartar
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
