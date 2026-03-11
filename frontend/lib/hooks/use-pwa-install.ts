"use client";

import { useState, useEffect, useCallback } from "react";

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
  prompt(): Promise<void>;
}

const VISIT_COUNT_KEY = "dentalos_visit_count";
const DISMISS_KEY = "dentalos_install_dismissed";
const VISIT_THRESHOLD = 3;

/**
 * Hook to handle PWA install prompt.
 *
 * Shows the install banner only after the user has visited the app
 * at least VISIT_THRESHOLD times and has not permanently dismissed it.
 *
 * Returns:
 * - canInstall: whether the browser supports install AND threshold met AND not dismissed
 * - isInstalled: whether the app is already installed (standalone mode)
 * - promptInstall: function to trigger the install prompt
 * - dismiss: function to permanently dismiss the install banner
 */
export function useInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [meetsThreshold, setMeetsThreshold] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    // Check if already in standalone mode
    if (window.matchMedia("(display-mode: standalone)").matches) {
      setIsInstalled(true);
      return;
    }

    // Check if user permanently dismissed
    if (localStorage.getItem(DISMISS_KEY) === "true") {
      setIsDismissed(true);
      return;
    }

    // Increment visit count
    const count = parseInt(localStorage.getItem(VISIT_COUNT_KEY) || "0", 10) + 1;
    localStorage.setItem(VISIT_COUNT_KEY, String(count));
    setMeetsThreshold(count >= VISIT_THRESHOLD);

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    window.addEventListener("beforeinstallprompt", handler);

    // Listen for successful install
    const installHandler = () => {
      setIsInstalled(true);
      setDeferredPrompt(null);
    };
    window.addEventListener("appinstalled", installHandler);

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      window.removeEventListener("appinstalled", installHandler);
    };
  }, []);

  const promptInstall = useCallback(async () => {
    if (!deferredPrompt) return;

    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;

    if (outcome === "accepted") {
      setIsInstalled(true);
    }
    setDeferredPrompt(null);
  }, [deferredPrompt]);

  const dismiss = useCallback(() => {
    localStorage.setItem(DISMISS_KEY, "true");
    setIsDismissed(true);
  }, []);

  return {
    canInstall: !!deferredPrompt && !isInstalled && meetsThreshold && !isDismissed,
    isInstalled,
    promptInstall,
    dismiss,
  };
}
