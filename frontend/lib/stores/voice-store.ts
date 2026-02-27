"use client";

import { create } from "zustand";
import type { VoiceFinding, ApplyResponse } from "@/lib/hooks/use-voice";

// ─── Types ────────────────────────────────────────────────────────────────────

export type VoicePhase =
  | "idle"
  | "patient_select"
  | "recording"
  | "processing"
  | "reviewing"
  | "success";

export type VoiceContext = "odontogram" | "evolution" | "general";
export type VoiceEntryPoint = "global_fab" | "contextual";

interface VoiceState {
  session_id: string | null;
  patient_id: string | null;
  patient_name: string | null;
  context: VoiceContext;
  phase: VoicePhase;
  entry_point: VoiceEntryPoint | null;
  findings: VoiceFinding[];
  warnings: string[];
  filtered_speech: string[];
  apply_result: ApplyResponse | null;

  // Actions
  start_global: () => void;
  start_contextual: (patient_id: string, patient_name: string) => void;
  set_session: (session_id: string) => void;
  set_phase: (phase: VoicePhase) => void;
  set_patient: (patient_id: string, patient_name: string) => void;
  set_findings: (findings: VoiceFinding[], warnings: string[], filtered_speech: string[]) => void;
  set_apply_result: (result: ApplyResponse) => void;
  reset: () => void;
  is_active: () => boolean;
}

// ─── Initial state ───────────────────────────────────────────────────────────

const INITIAL_STATE: {
  session_id: null;
  patient_id: null;
  patient_name: null;
  context: VoiceContext;
  phase: VoicePhase;
  entry_point: null;
  findings: VoiceFinding[];
  warnings: string[];
  filtered_speech: string[];
  apply_result: null;
} = {
  session_id: null,
  patient_id: null,
  patient_name: null,
  context: "general",
  phase: "idle",
  entry_point: null,
  findings: [],
  warnings: [],
  filtered_speech: [],
  apply_result: null,
};

// ─── Store ────────────────────────────────────────────────────────────────────

export const useVoiceStore = create<VoiceState>((set, get) => ({
  ...INITIAL_STATE,

  start_global: () => {
    if (get().phase !== "idle") return;
    set({
      ...INITIAL_STATE,
      phase: "patient_select",
      entry_point: "global_fab",
      context: "odontogram",
    });
  },

  start_contextual: (patient_id: string, patient_name: string) => {
    if (get().phase !== "idle") return;
    set({
      ...INITIAL_STATE,
      patient_id,
      patient_name,
      phase: "recording",
      entry_point: "contextual",
      context: "odontogram",
    });
  },

  set_session: (session_id: string) => {
    set({ session_id });
  },

  set_phase: (phase: VoicePhase) => {
    set({ phase });
  },

  set_patient: (patient_id: string, patient_name: string) => {
    set({ patient_id, patient_name });
  },

  set_findings: (findings, warnings, filtered_speech) => {
    set({ findings, warnings, filtered_speech, phase: "reviewing" });
  },

  set_apply_result: (result: ApplyResponse) => {
    set({ apply_result: result, phase: "success" });
  },

  reset: () => {
    set({ ...INITIAL_STATE });
  },

  is_active: () => {
    const phase = get().phase;
    return phase !== "idle" && phase !== "success";
  },
}));
