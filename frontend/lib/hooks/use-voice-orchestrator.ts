"use client";

import * as React from "react";
import {
  useCreateVoiceSession,
  useUploadAudio,
  useTranscriptionStatus,
  useParseTranscription,
  type ParseResponse,
} from "@/lib/hooks/use-voice";
import { useToast } from "@/lib/hooks/use-toast";
import type { VoiceContext } from "@/lib/stores/voice-store";
import {
  createRecordingEntry,
  persistChunk,
  updateRecordingStatus,
  updateRecordingSessionId,
  updateRecordingElapsed,
  cleanupRecording,
} from "@/lib/voice-persistence";

// ─── Constants ────────────────────────────────────────────────────────────────

const WAVEFORM_BAR_COUNT = 16;
/** Max time (ms) to wait for transcription + parsing before timing out */
const PROCESSING_TIMEOUT_MS = 90_000;
/** Max recording duration (5 min). WebM/Opus at ~15KB/s ≈ 4.5 MB — well under Whisper's 25 MB limit. */
const MAX_RECORDING_MS = 5 * 60 * 1_000;
/** Timeslice for MediaRecorder — flush chunks every 10s for progressive IDB persistence */
const TIMESLICE_MS = 10_000;

// ─── Types ────────────────────────────────────────────────────────────────────

export type OrchestratorPhase =
  | "idle"
  | "requesting_mic"
  | "recording"
  | "stopping"
  | "processing"
  | "parsing"
  | "done"
  | "error";

interface UseVoiceOrchestratorOptions {
  patient_id: string;
  patient_name?: string;
  context: VoiceContext;
  /** Called when session is created (provides session_id) */
  on_session_created?: (session_id: string) => void;
  /** Called when parse results are ready */
  on_parse_complete?: (results: ParseResponse) => void;
  /** Called on error */
  on_error?: (message: string) => void;
}

interface UseVoiceOrchestratorReturn {
  session_id: string | null;
  phase: OrchestratorPhase;
  elapsed_seconds: number;
  frequency_data: number[];
  is_media_recorder_supported: boolean;
  start_recording: () => Promise<void>;
  stop_recording: () => void;
  cancel: (opts?: { discard?: boolean }) => void;
  parse_results: ParseResponse | null;
  error: string | null;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useVoiceOrchestrator(
  options: UseVoiceOrchestratorOptions,
): UseVoiceOrchestratorReturn {
  const { patient_id, patient_name, context, on_session_created, on_parse_complete, on_error } = options;

  // ─── State ────────────────────────────────────────────────────────────────
  const [phase, setPhase] = React.useState<OrchestratorPhase>("idle");
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = React.useState(0);
  const [frequencyData, setFrequencyData] = React.useState<number[]>(
    () => new Array(WAVEFORM_BAR_COUNT).fill(0),
  );
  const [parseResults, setParseResults] = React.useState<ParseResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  // ─── Refs ─────────────────────────────────────────────────────────────────
  const mediaRecorderRef = React.useRef<MediaRecorder | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const chunksRef = React.useRef<Blob[]>([]);
  const timerRef = React.useRef<ReturnType<typeof setInterval> | null>(null);
  const maxDurationTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const animationFrameRef = React.useRef<number | null>(null);
  const analyserRef = React.useRef<AnalyserNode | null>(null);
  const audioContextRef = React.useRef<AudioContext | null>(null);
  const mimeTypeRef = React.useRef<string>("audio/webm");
  const isCancelledRef = React.useRef(false);
  const processingTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionIdRef = React.useRef<string | null>(null);

  // New refs for IDB persistence
  const recordingIdRef = React.useRef<string | null>(null);
  const idempotencyKeyRef = React.useRef<string | null>(null);
  const chunkIndexCounterRef = React.useRef(0);

  // ─── Hooks ────────────────────────────────────────────────────────────────
  const { mutateAsync: createSession } = useCreateVoiceSession();
  const { mutateAsync: uploadAudio } = useUploadAudio();
  const { mutateAsync: parseTranscription } = useParseTranscription();
  const { error: showError, warning: showWarning } = useToast();

  // ─── Reset state when patient changes ───────────────────────────────────
  React.useEffect(() => {
    // If patient changes mid-flow, abort any in-progress recording and reset
    cleanupMedia();
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = null;
    }
    isCancelledRef.current = true;
    setPhase("idle");
    setSessionId(null);
    sessionIdRef.current = null;
    setElapsedSeconds(0);
    setParseResults(null);
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patient_id]);

  // Poll transcription status only when in processing phase
  const shouldPollStatus = phase === "processing" && sessionId !== null;
  const { data: transcriptionStatus } = useTranscriptionStatus(
    shouldPollStatus ? sessionId : null,
  );

  // ─── Browser compatibility ────────────────────────────────────────────────
  const isMediaRecorderSupported = React.useMemo(() => {
    if (typeof window === "undefined") return false;
    return Boolean(
      typeof navigator.mediaDevices?.getUserMedia === "function" &&
        typeof MediaRecorder !== "undefined",
    );
  }, []);

  // ─── Waveform animation ───────────────────────────────────────────────────

  const startWaveformAnimation = React.useCallback((analyser: AnalyserNode) => {
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    function animate() {
      analyser.getByteFrequencyData(dataArray);
      const step = Math.floor(dataArray.length / WAVEFORM_BAR_COUNT);
      const bars: number[] = [];
      for (let i = 0; i < WAVEFORM_BAR_COUNT; i++) {
        bars.push(dataArray[i * step] / 255);
      }
      setFrequencyData(bars);
      animationFrameRef.current = requestAnimationFrame(animate);
    }

    animate();
  }, []);

  const stopWaveformAnimation = React.useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    setFrequencyData(new Array(WAVEFORM_BAR_COUNT).fill(0));
  }, []);

  // ─── Upload the complete blob ───────────────────────────────────────────

  const uploadChunk = React.useCallback(
    async (blob: Blob, index: number, sid: string, idempotencyKey?: string) => {
      const rid = recordingIdRef.current;

      // Check online status — if offline, keep data in IDB for recovery
      if (typeof navigator !== "undefined" && !navigator.onLine) {
        if (rid) await updateRecordingStatus(rid, "failed", "Sin conexion a internet");
        showWarning(
          "Sin conexion",
          "El audio se guardo localmente. Se subira cuando se recupere la conexion.",
        );
        return;
      }

      try {
        if (rid) await updateRecordingStatus(rid, "uploading");
        await uploadAudio({
          sessionId: sid,
          audioBlob: blob,
          chunkIndex: index,
          idempotencyKey,
        });
        // Upload succeeded — clean up IDB data
        if (rid) {
          await updateRecordingStatus(rid, "uploaded");
          await cleanupRecording(rid);
        }
      } catch {
        // Upload failed — IDB data remains for recovery
        if (rid) await updateRecordingStatus(rid, "failed", "Error al subir el audio");
      }
    },
    [uploadAudio, showWarning],
  );

  // ─── Cleanup media ────────────────────────────────────────────────────────

  const cleanupMedia = React.useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (maxDurationTimerRef.current) {
      clearTimeout(maxDurationTimerRef.current);
      maxDurationTimerRef.current = null;
    }
    stopWaveformAnimation();

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }

    mediaRecorderRef.current = null;
    analyserRef.current = null;
  }, [stopWaveformAnimation]);

  // ─── Start recording ──────────────────────────────────────────────────────

  const startRecording = React.useCallback(async () => {
    if (phase !== "idle" && phase !== "done" && phase !== "error") return;

    // Reset all state from any previous recording (same or different patient)
    isCancelledRef.current = false;
    setSessionId(null);
    sessionIdRef.current = null;
    setElapsedSeconds(0);
    setError(null);
    setParseResults(null);
    chunkIndexCounterRef.current = 0;
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = null;
    }
    setPhase("requesting_mic");

    // Generate client-side IDs for IDB persistence + idempotency
    const recordingId = crypto.randomUUID();
    const idempotencyKey = crypto.randomUUID();
    recordingIdRef.current = recordingId;
    idempotencyKeyRef.current = idempotencyKey;

    // 1. Create session (server-side)
    let sid: string | null = null;
    try {
      const session = await createSession({ patient_id, context });
      sid = session.id;
      setSessionId(sid);
      sessionIdRef.current = sid;
      on_session_created?.(sid);
    } catch {
      // Session creation failed — recording can still proceed with IDB persistence.
      // Recovery hook will call createSession later.
    }

    // Persist recording metadata to IndexedDB (fire-and-forget — never block recording)
    createRecordingEntry({
      recording_id: recordingId,
      session_id: sid,
      patient_id,
      patient_name: patient_name || "",
      context,
      mime_type: "audio/webm",
      started_at: Date.now(),
      elapsed_seconds: 0,
      idempotency_key: idempotencyKey,
    }).catch(() => {});

    // If session creation failed, update IDB and bail
    if (!sid) {
      setPhase("error");
      setError("No se pudo crear la sesion de voz.");
      on_error?.("No se pudo crear la sesion de voz.");
      updateRecordingStatus(recordingId, "failed", "No se pudo crear sesion").catch(() => {});
      return;
    }

    // Update IDB with session_id (fire-and-forget)
    updateRecordingSessionId(recordingId, sid).catch(() => {});

    // 2. Request mic access
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      if (err instanceof DOMException && err.name === "NotAllowedError") {
        const msg = "Permiso de microfono denegado. Habilite el acceso en la configuracion del navegador.";
        showError("Microfono denegado", msg);
        setError(msg);
      } else if (err instanceof DOMException && err.name === "NotFoundError") {
        const msg = "No se detecto ningun microfono conectado.";
        showError("Sin microfono", msg);
        setError(msg);
      } else {
        const msg = "Error al acceder al microfono.";
        showError("Error de microfono", msg);
        setError(msg);
      }
      setPhase("error");
      on_error?.("Error de microfono");
      cleanupRecording(recordingId).catch(() => {});
      return;
    }

    if (isCancelledRef.current) {
      stream.getTracks().forEach((t) => t.stop());
      return;
    }

    streamRef.current = stream;

    // 3. Set up WebAudio analyser
    const audioCtx = new AudioContext();
    audioContextRef.current = audioCtx;
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    analyserRef.current = analyser;

    // 4. Determine MIME type
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";
    mimeTypeRef.current = mimeType;

    // 5. Create MediaRecorder with 10s timeslice for progressive IDB persistence
    const recorder = new MediaRecorder(stream, { mimeType });
    mediaRecorderRef.current = recorder;
    chunksRef.current = [];

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        const idx = chunkIndexCounterRef.current++;
        chunksRef.current.push(event.data);
        // Fire-and-forget persist to IndexedDB
        persistChunk(recordingId, idx, event.data).catch(() => {});
      }
    };

    recorder.onstart = () => {
      setPhase("recording");
      setElapsedSeconds(0);
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => {
          const next = prev + 1;
          // Periodically update elapsed_seconds in IDB (every 10s)
          if (next % 10 === 0) {
            updateRecordingElapsed(recordingId, next).catch(() => {});
          }
          return next;
        });
      }, 1_000);
    };

    recorder.onstop = () => {
      // Mark recording as stopped in IDB
      updateRecordingStatus(recordingId, "stopped").catch(() => {});

      // Upload the complete recording as a single file
      if (chunksRef.current.length > 0 && !isCancelledRef.current) {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        chunksRef.current = [];
        uploadChunk(blob, 0, sessionIdRef.current ?? sid!, idempotencyKey);
      }
    };

    // 6. Start with timeslice — ondataavailable fires every 10s
    recorder.start(TIMESLICE_MS);
    startWaveformAnimation(analyser);

    // 7. Auto-stop at max duration to prevent oversized files
    maxDurationTimerRef.current = setTimeout(() => {
      if (recorder.state === "recording") {
        recorder.stop();
        cleanupMedia();
        setPhase("processing");
      }
    }, MAX_RECORDING_MS);
  }, [
    phase,
    patient_id,
    patient_name,
    context,
    createSession,
    on_session_created,
    on_error,
    showError,
    uploadChunk,
    startWaveformAnimation,
    cleanupMedia,
  ]);

  // ─── Stop recording ───────────────────────────────────────────────────────

  const stopRecording = React.useCallback(() => {
    if (phase !== "recording") return;
    setPhase("stopping");

    // Stop the recorder — this triggers onstop which uploads the full blob
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }

    // Clean up media tracks and timers (but recorder.onstop fires first)
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (maxDurationTimerRef.current) {
      clearTimeout(maxDurationTimerRef.current);
      maxDurationTimerRef.current = null;
    }
    stopWaveformAnimation();

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }

    mediaRecorderRef.current = null;
    analyserRef.current = null;

    // Transition to processing — poll transcription status
    setPhase("processing");
  }, [phase, stopWaveformAnimation]);

  // ─── Cancel ───────────────────────────────────────────────────────────────

  const cancel = React.useCallback(
    (opts?: { discard?: boolean }) => {
      isCancelledRef.current = true;
      cleanupMedia();
      if (processingTimeoutRef.current) {
        clearTimeout(processingTimeoutRef.current);
        processingTimeoutRef.current = null;
      }

      // Only clean up IDB when explicitly discarding (user pressed cancel)
      if (opts?.discard && recordingIdRef.current) {
        cleanupRecording(recordingIdRef.current).catch(() => {});
      }

      setPhase("idle");
      setSessionId(null);
      setElapsedSeconds(0);
      setParseResults(null);
      setError(null);
    },
    [cleanupMedia],
  );

  // ─── Visibility change guard (iOS Safari) ─────────────────────────────────

  React.useEffect(() => {
    function handleVisibilityChange() {
      if (document.visibilityState === "hidden" && mediaRecorderRef.current?.state === "recording") {
        // Force-flush current audio segment to ondataavailable → IndexedDB
        try {
          mediaRecorderRef.current.requestData();
        } catch {
          // requestData may throw if recorder is in an unexpected state
        }
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  // ─── Processing timeout ──────────────────────────────────────────────────

  React.useEffect(() => {
    if (phase === "processing" || phase === "parsing") {
      processingTimeoutRef.current = setTimeout(() => {
        setPhase("error");
        setError(
          "El procesamiento tardó demasiado. Esto puede ocurrir si el servicio de " +
          "transcripción o análisis no está disponible. Intente de nuevo.",
        );
        on_error?.("Timeout de procesamiento");
      }, PROCESSING_TIMEOUT_MS);

      return () => {
        if (processingTimeoutRef.current) {
          clearTimeout(processingTimeoutRef.current);
          processingTimeoutRef.current = null;
        }
      };
    }
  }, [phase, on_error]);

  // ─── Auto-parse when transcriptions complete ──────────────────────────────

  React.useEffect(() => {
    if (phase !== "processing" || !sessionId) return;
    if (!transcriptionStatus?.all_completed) return;

    // All transcriptions complete — auto-trigger parse
    setPhase("parsing");

    parseTranscription(sessionId)
      .then((results) => {
        setParseResults(results);
        setPhase("done");
        on_parse_complete?.(results);
      })
      .catch(() => {
        setPhase("error");
        setError("No se pudo analizar la transcripcion.");
        on_error?.("Error al analizar transcripcion");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, sessionId, transcriptionStatus?.all_completed]);

  // ─── Cleanup on unmount ───────────────────────────────────────────────────
  // Do NOT discard IDB data on unmount — leave for recovery hook

  React.useEffect(() => {
    return () => {
      cleanupMedia();
    };
  }, [cleanupMedia]);

  return {
    session_id: sessionId,
    phase,
    elapsed_seconds: elapsedSeconds,
    frequency_data: frequencyData,
    is_media_recorder_supported: isMediaRecorderSupported,
    start_recording: startRecording,
    stop_recording: stopRecording,
    cancel,
    parse_results: parseResults,
    error,
  };
}
