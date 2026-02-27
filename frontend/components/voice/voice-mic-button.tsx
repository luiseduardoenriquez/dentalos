"use client";

import * as React from "react";
import { Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { VoiceAddonUpsell } from "@/components/voice/voice-addon-upsell";
import { useAuth } from "@/lib/hooks/use-auth";
import { useVoiceStore } from "@/lib/stores/voice-store";
import { cn } from "@/lib/utils";

interface VoiceMicButtonProps {
  /** Called when voice recording should start (feature is enabled) */
  onActivate: () => void;
  /** Whether voice is currently active for this context */
  isActive?: boolean;
  className?: string;
}

/**
 * Mic button for the odontogram toolbar.
 * Shows upsell dialog when feature is disabled, activates voice when enabled.
 */
export function VoiceMicButton({ onActivate, isActive = false, className }: VoiceMicButtonProps) {
  const { has_feature } = useAuth();
  const voicePhase = useVoiceStore((s) => s.phase);
  const hasVoice = has_feature("voice_dictation");
  const isBusy = voicePhase !== "idle" && voicePhase !== "success";
  const [showUpsell, setShowUpsell] = React.useState(false);

  if (!hasVoice) {
    return (
      <>
        <Button
          variant="outline"
          size="sm"
          className={cn("opacity-60", className)}
          title="Dictado por voz (complemento)"
          onClick={() => setShowUpsell(true)}
        >
          <MicOff className="mr-1.5 h-3.5 w-3.5" />
          Voz
        </Button>

        <Dialog open={showUpsell} onOpenChange={setShowUpsell}>
          <DialogContent size="sm">
            <DialogHeader>
              <DialogTitle>Complemento de Voz</DialogTitle>
            </DialogHeader>
            <VoiceAddonUpsell variant="popover" />
          </DialogContent>
        </Dialog>
      </>
    );
  }

  return (
    <Button
      variant={isActive ? "default" : "outline"}
      size="sm"
      onClick={onActivate}
      disabled={isBusy && !isActive}
      className={cn(isActive && "bg-primary-600 text-white", className)}
      title={isActive ? "Sesion de voz activa" : "Iniciar dictado por voz"}
    >
      <Mic className={cn("mr-1.5 h-3.5 w-3.5", isActive && "animate-pulse")} />
      {isActive ? "Grabando..." : "Voz"}
    </Button>
  );
}
