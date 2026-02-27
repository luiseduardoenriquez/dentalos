"use client";

import * as React from "react";
import { Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { VoiceQuickStartModal } from "@/components/voice/voice-quick-start-modal";
import { VoiceAddonUpsell } from "@/components/voice/voice-addon-upsell";
import { useAuth } from "@/lib/hooks/use-auth";
import { useVoiceStore } from "@/lib/stores/voice-store";
import { useVoiceNavigationGuard } from "@/lib/hooks/use-voice-navigation-guard";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

/**
 * Persistent floating action button for voice dictation.
 * Visible on all dashboard pages after login.
 * Opens the VoiceQuickStartModal on click (or upsell if feature disabled).
 */
export function GlobalVoiceFab() {
  const { has_feature, is_authenticated } = useAuth();
  const voiceStore = useVoiceStore();
  const { warning } = useToast();
  const hasVoice = has_feature("voice_dictation");

  const [modalOpen, setModalOpen] = React.useState(false);
  const [showUpsell, setShowUpsell] = React.useState(false);

  useVoiceNavigationGuard();

  // Don't render for unauthenticated users
  if (!is_authenticated) return null;

  // Don't render when contextual voice is active (avoid two FABs)
  if (voiceStore.entry_point === "contextual" && voiceStore.phase !== "idle") return null;

  function handleClick() {
    if (!hasVoice) {
      setShowUpsell(true);
      return;
    }

    // Check for concurrent session
    if (voiceStore.phase !== "idle" && voiceStore.phase !== "success") {
      warning("Sesion activa", "Ya tiene una sesion de voz activa.");
      return;
    }

    voiceStore.start_global();
    setModalOpen(true);
  }

  function handleModalChange(open: boolean) {
    setModalOpen(open);
    if (!open) {
      // Reset store when modal closes
      voiceStore.reset();
    }
  }

  const isActive = voiceStore.entry_point === "global_fab" && voiceStore.phase !== "idle";

  return (
    <>
      {/* FAB button */}
      <Button
        size="icon"
        className={cn(
          "fixed bottom-6 right-6 z-40 h-14 w-14 rounded-full shadow-lg",
          "bg-primary-600 hover:bg-primary-700 text-white",
          isActive && "animate-pulse ring-2 ring-primary-400 ring-offset-2",
        )}
        onClick={handleClick}
        title="Dictado por voz"
      >
        <Mic className="h-6 w-6" />
      </Button>

      {/* Voice quick-start modal */}
      <VoiceQuickStartModal open={modalOpen} onOpenChange={handleModalChange} />

      {/* Upsell dialog for non-subscribers */}
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
