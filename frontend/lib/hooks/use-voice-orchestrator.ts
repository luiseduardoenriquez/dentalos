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

// ─── Constants ────────────────────────────────────────────────────────────────

const CHUNK_DURATION_MS = 30_000;
const WAVEFORM_BAR_COUNT = 16;
/** Max time (ms) to wait for transcription + parsing before timing out */
const PROCESSING_TIMEOUT_MS = 90_000;

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
  cancel: () => void;
  parse_results: ParseResponse | null;
  error: string | null;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useVoiceOrchestrator(
  options: UseVoiceOrchestratorOptions,
): UseVoiceOrchestratorReturn {
  const { patient_id, context, on_session_created, on_parse_complete, on_error } = options;

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
  const chunkIndexRef = React.useRef(0);
  const timerRef = React.useRef<ReturnType<typeof setInterval> | null>(null);
  const chunkIntervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null);
  const animationFrameRef = React.useRef<number | null>(null);
  const analyserRef = React.useRef<AnalyserNode | null>(null);
  const audioContextRef = React.useRef<AudioContext | null>(null);
  const pendingUploadsRef = React.useRef(0);
  const mimeTypeRef = React.useRef<string>("audio/webm");
  const isCancelledRef = React.useRef(false);
  const processingTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // ─── Hooks ────────────────────────────────────────────────────────────────
  const { mutateAsync: createSession } = useCreateVoiceSession();
  const { mutateAsync: uploadAudio } = useUploadAudio();
  const { mutateAsync: parseTranscription } = useParseTranscription();
  const { error: showError } = useToast();

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

  // ─── Upload a chunk ───────────────────────────────────────────────────────

  const uploadChunk = React.useCallback(
    async (blob: Blob, index: number, sid: string) => {
      pendingUploadsRef.current += 1;
      try {
        await uploadAudio({ sessionId: sid, audioBlob: blob, chunkIndex: index });
      } catch {
        // Error toast handled by useUploadAudio hook
      } finally {
        pendingUploadsRef.current -= 1;
      }
    },
    [uploadAudio],
  );

  // ─── Cleanup media ────────────────────────────────────────────────────────

  const cleanupMedia = React.useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current);
      chunkIntervalRef.current = null;
    }
    stopWaveformAnimation();

    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }

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
    if (phase !== "idle" && phase !== "done") return;

    isCancelledRef.current = false;
    setError(null);
    setParseResults(null);
    setPhase("requesting_mic");

    // 1. Create session
    let sid: string;
    try {
      const session = await createSession({ patient_id, context });
      sid = session.id;
      setSessionId(sid);
      on_session_created?.(sid);
    } catch {
      setPhase("error");
      setError("No se pudo crear la sesion de voz.");
      on_error?.("No se pudo crear la sesion de voz.");
      return;
    }

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

    // 5. Create MediaRecorder
    const recorder = new MediaRecorder(stream, { mimeType });
    mediaRecorderRef.current = recorder;
    chunksRef.current = [];
    chunkIndexRef.current = 0;
    pendingUploadsRef.current = 0;

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onstart = () => {
      setPhase("recording");
      setElapsedSeconds(0);
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1_000);
    };

    recorder.onstop = () => {
      // Upload last chunk
      if (chunksRef.current.length > 0) {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const currentIndex = chunkIndexRef.current;
        chunkIndexRef.current += 1;
        chunksRef.current = [];
        uploadChunk(blob, currentIndex, sid);
      }
    };

    // 6. Start
    recorder.start(CHUNK_DURATION_MS);
    startWaveformAnimation(analyser);

    // 7. Auto-chunk interval
    chunkIntervalRef.current = setInterval(() => {
      if (recorder.state === "recording") {
        recorder.requestData();
        if (chunksRef.current.length > 0) {
          const blob = new Blob(chunksRef.current, { type: mimeType });
          const currentIndex = chunkIndexRef.current;
          chunkIndexRef.current += 1;
          chunksRef.current = [];
          uploadChunk(blob, currentIndex, sid);
        }
      }
    }, CHUNK_DURATION_MS);
  }, [
    phase,
    patient_id,
    context,
    createSession,
    on_session_created,
    on_error,
    showError,
    uploadChunk,
    startWaveformAnimation,
  ]);

  // ─── Stop recording ───────────────────────────────────────────────────────

  const stopRecording = React.useCallback(() => {
    if (phase !== "recording") return;
    setPhase("stopping");
    cleanupMedia();
    // Transition to processing — wait for uploads to drain, then poll status
    setPhase("processing");
  }, [phase, cleanupMedia]);

  // ─── Cancel ───────────────────────────────────────────────────────────────

  const cancel = React.useCallback(() => {
    isCancelledRef.current = true;
    cleanupMedia();
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = null;
    }
    setPhase("idle");
    setSessionId(null);
    setElapsedSeconds(0);
    setParseResults(null);
    setError(null);
  }, [cleanupMedia]);

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
