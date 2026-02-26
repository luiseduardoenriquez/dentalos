"use client";

import * as React from "react";
import { Mic, MicOff, Square, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUploadAudio } from "@/lib/hooks/use-voice";
import { useToast } from "@/lib/hooks/use-toast";
import { cn } from "@/lib/utils";

// ─── Constants ────────────────────────────────────────────────────────────────

/** Maximum chunk duration in milliseconds (30 seconds) */
const CHUNK_DURATION_MS = 30_000;

/** Number of frequency bars for the waveform visualization */
const WAVEFORM_BAR_COUNT = 16;

// ─── Types ────────────────────────────────────────────────────────────────────

type RecordingState = "idle" | "recording" | "uploading" | "done";

interface VoiceRecordingButtonProps {
  /** Active session ID — recording is disabled when null */
  sessionId: string | null;
  /** Callback fired after each audio chunk upload completes */
  onUploadComplete?: () => void;
  /** Additional CSS class for the container */
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * Floating action button for voice recording.
 * Records audio using the MediaRecorder API in webm/opus format.
 * Automatically splits recording into 30-second chunks and uploads each.
 *
 * Positioned fixed at the bottom-right of the viewport.
 */
export function VoiceRecordingButton({
  sessionId,
  onUploadComplete,
  className,
}: VoiceRecordingButtonProps) {
  // ─── State ──────────────────────────────────────────────────────────────────
  const [state, setState] = React.useState<RecordingState>("idle");
  const [elapsedSeconds, setElapsedSeconds] = React.useState(0);
  const [frequencyData, setFrequencyData] = React.useState<number[]>(
    () => new Array(WAVEFORM_BAR_COUNT).fill(0),
  );

  // ─── Refs ───────────────────────────────────────────────────────────────────
  const mediaRecorderRef = React.useRef<MediaRecorder | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const chunksRef = React.useRef<Blob[]>([]);
  const chunkIndexRef = React.useRef(0);
  const timerRef = React.useRef<ReturnType<typeof setInterval> | null>(null);
  const animationFrameRef = React.useRef<number | null>(null);
  const analyserRef = React.useRef<AnalyserNode | null>(null);
  const pendingUploadsRef = React.useRef(0);

  // ─── Hooks ──────────────────────────────────────────────────────────────────
  const { mutateAsync: uploadAudio } = useUploadAudio();
  const { error: showError, warning: showWarning } = useToast();

  // ─── Cleanup on unmount ─────────────────────────────────────────────────────
  React.useEffect(() => {
    return () => {
      stopRecording();
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── Check browser compatibility ───────────────────────────────────────────
  const isMediaRecorderSupported = React.useMemo(() => {
    if (typeof window === "undefined") return false;
    return Boolean(typeof navigator.mediaDevices?.getUserMedia === "function" && typeof MediaRecorder !== "undefined");
  }, []);

  // ─── Waveform animation ─────────────────────────────────────────────────────

  function startWaveformAnimation(analyser: AnalyserNode) {
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    function animate() {
      analyser.getByteFrequencyData(dataArray);

      // Sample evenly-spaced bars from the frequency data
      const step = Math.floor(dataArray.length / WAVEFORM_BAR_COUNT);
      const bars: number[] = [];
      for (let i = 0; i < WAVEFORM_BAR_COUNT; i++) {
        // Normalize to 0-1 range
        bars.push(dataArray[i * step] / 255);
      }
      setFrequencyData(bars);

      animationFrameRef.current = requestAnimationFrame(animate);
    }

    animate();
  }

  function stopWaveformAnimation() {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    setFrequencyData(new Array(WAVEFORM_BAR_COUNT).fill(0));
  }

  // ─── Upload a single chunk ──────────────────────────────────────────────────

  async function uploadChunk(blob: Blob, index: number) {
    if (!sessionId) return;

    pendingUploadsRef.current += 1;
    try {
      await uploadAudio({ sessionId, audioBlob: blob, chunkIndex: index });
      onUploadComplete?.();
    } catch {
      // Error toast is handled by the useUploadAudio hook
    } finally {
      pendingUploadsRef.current -= 1;
      // Transition to done only if recording has stopped and all uploads are complete
      if (mediaRecorderRef.current?.state !== "recording" && pendingUploadsRef.current === 0) {
        setState("done");
      }
    }
  }

  // ─── Start recording ────────────────────────────────────────────────────────

  async function startRecording() {
    if (!sessionId) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Set up Web Audio API analyser for waveform visualization
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Determine supported MIME type
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/mp4";

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      chunkIndexRef.current = 0;
      pendingUploadsRef.current = 0;

      // Collect data as it becomes available
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      // Auto-chunk: every CHUNK_DURATION_MS, stop/restart to upload a chunk
      recorder.onstart = () => {
        setState("recording");
        setElapsedSeconds(0);

        // Elapsed time counter
        timerRef.current = setInterval(() => {
          setElapsedSeconds((prev) => prev + 1);
        }, 1_000);
      };

      // When a timeslice ends or stop() is called, package the chunk and upload
      recorder.onstop = () => {
        if (chunksRef.current.length > 0) {
          const blob = new Blob(chunksRef.current, { type: mimeType });
          const currentIndex = chunkIndexRef.current;
          chunkIndexRef.current += 1;
          chunksRef.current = [];

          // Upload in background
          setState("uploading");
          uploadChunk(blob, currentIndex);
        } else {
          setState("done");
        }
      };

      // Start recording with timeslice for chunk-based recording
      recorder.start(CHUNK_DURATION_MS);
      startWaveformAnimation(analyser);

      // Auto-upload chunks: periodically request data and restart
      const chunkInterval = setInterval(() => {
        if (recorder.state === "recording") {
          // Request data triggers ondataavailable, then we upload
          recorder.requestData();
          if (chunksRef.current.length > 0) {
            const blob = new Blob(chunksRef.current, { type: mimeType });
            const currentIndex = chunkIndexRef.current;
            chunkIndexRef.current += 1;
            chunksRef.current = [];
            uploadChunk(blob, currentIndex);
          }
        } else {
          clearInterval(chunkInterval);
        }
      }, CHUNK_DURATION_MS);

      // Store interval ref for cleanup
      (recorder as unknown as Record<string, unknown>).__chunkInterval = chunkInterval;
    } catch (err) {
      if (err instanceof DOMException && err.name === "NotAllowedError") {
        showError(
          "Permiso de microfono denegado",
          "Habilite el acceso al microfono en la configuracion del navegador.",
        );
      } else if (err instanceof DOMException && err.name === "NotFoundError") {
        showError(
          "Microfono no encontrado",
          "No se detecto ningun microfono conectado al dispositivo.",
        );
      } else {
        showError(
          "Error al iniciar grabacion",
          "Ocurrio un error inesperado al acceder al microfono.",
        );
      }
      setState("idle");
    }
  }

  // ─── Stop recording ─────────────────────────────────────────────────────────

  function stopRecording() {
    // Clear elapsed timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    // Stop waveform animation
    stopWaveformAnimation();

    // Clear chunk interval
    const recorder = mediaRecorderRef.current;
    if (recorder) {
      const chunkInterval = (recorder as unknown as Record<string, unknown>).__chunkInterval as
        | ReturnType<typeof setInterval>
        | undefined;
      if (chunkInterval) {
        clearInterval(chunkInterval);
      }
    }

    // Stop the MediaRecorder (triggers onstop → upload last chunk)
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }

    // Stop the media stream tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    mediaRecorderRef.current = null;
    analyserRef.current = null;
  }

  // ─── Formatted elapsed time ─────────────────────────────────────────────────

  const formattedTime = React.useMemo(() => {
    const minutes = Math.floor(elapsedSeconds / 60);
    const seconds = elapsedSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }, [elapsedSeconds]);

  // ─── Click handler ──────────────────────────────────────────────────────────

  function handleClick() {
    if (state === "recording") {
      stopRecording();
    } else if (state === "idle" || state === "done") {
      startRecording();
    }
  }

  // ─── Derived state ──────────────────────────────────────────────────────────

  const isDisabled = !sessionId || !isMediaRecorderSupported || state === "uploading";
  const isRecording = state === "recording";
  const isUploading = state === "uploading";

  // Show warning if browser doesn't support MediaRecorder
  React.useEffect(() => {
    if (!isMediaRecorderSupported && typeof window !== "undefined") {
      showWarning(
        "Navegador no compatible",
        "Su navegador no soporta grabacion de audio. Use Chrome, Edge o Firefox.",
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMediaRecorderSupported]);

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className={cn("fixed bottom-6 right-6 z-50 flex flex-col items-center gap-2", className)}>
      {/* Recording indicator: elapsed time + waveform */}
      {isRecording && (
        <div className="flex items-center gap-3 rounded-full bg-[hsl(var(--card))] px-4 py-2 shadow-lg border border-[hsl(var(--border))]">
          {/* Pulsing red dot */}
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-red-500" />
          </span>

          {/* Elapsed time */}
          <span className="text-sm font-mono font-medium tabular-nums text-foreground">
            {formattedTime}
          </span>

          {/* Waveform bars */}
          <div className="flex items-center gap-0.5 h-6">
            {frequencyData.map((value, i) => (
              <div
                key={i}
                className="w-0.5 rounded-full bg-primary-500 transition-all duration-75"
                style={{ height: `${Math.max(4, value * 24)}px` }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Uploading indicator */}
      {isUploading && (
        <div className="flex items-center gap-2 rounded-full bg-[hsl(var(--card))] px-4 py-2 shadow-lg border border-[hsl(var(--border))]">
          <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
          <span className="text-sm text-[hsl(var(--muted-foreground))]">Subiendo audio...</span>
        </div>
      )}

      {/* Main FAB button */}
      <Button
        variant={isRecording ? "destructive" : "default"}
        size="icon"
        className={cn(
          "h-14 w-14 rounded-full shadow-lg",
          isRecording && "animate-pulse",
          !sessionId && "opacity-50",
        )}
        disabled={isDisabled}
        onClick={handleClick}
        title={
          !sessionId
            ? "Inicie una sesion de voz primero"
            : isRecording
              ? "Detener grabacion"
              : "Iniciar grabacion"
        }
      >
        {isUploading ? (
          <Loader2 className="h-6 w-6 animate-spin" />
        ) : isRecording ? (
          <Square className="h-6 w-6" />
        ) : !isMediaRecorderSupported ? (
          <MicOff className="h-6 w-6" />
        ) : (
          <Mic className="h-6 w-6" />
        )}
      </Button>
    </div>
  );
}
