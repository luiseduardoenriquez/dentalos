"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, X, FileText, ImageIcon } from "lucide-react";

export interface UploadFile {
  id: string;
  file: File;
  preview?: string; // data URL for images
  progress: number; // 0-100
  error?: string;
}

export interface FileUploadProps {
  accept?: string; // e.g. "image/*,.pdf"
  maxFiles?: number; // default 5
  maxSizeMB?: number; // default 10
  multiple?: boolean; // default true
  onFilesChange: (files: UploadFile[]) => void;
  disabled?: boolean;
  className?: string;
}

type DragState = "idle" | "over" | "reject";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function parseAcceptedMimes(accept?: string): string[] {
  if (!accept) return [];
  return accept
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function isMimeAccepted(file: File, acceptedTypes: string[]): boolean {
  if (acceptedTypes.length === 0) return true;
  return acceptedTypes.some((type) => {
    if (type.endsWith("/*")) {
      const category = type.split("/")[0];
      return file.type.startsWith(`${category}/`);
    }
    if (type.startsWith(".")) {
      return file.name.toLowerCase().endsWith(type.toLowerCase());
    }
    return file.type === type;
  });
}

function getAcceptHint(accept?: string): string {
  if (!accept) return "";
  const types = parseAcceptedMimes(accept);
  const labels: string[] = [];
  types.forEach((t) => {
    if (t === "image/*") labels.push("imágenes");
    else if (t === "application/pdf" || t === ".pdf") labels.push("PDF");
    else if (t === ".dicom" || t === "application/dicom") labels.push("DICOM");
    else if (t === "image/jpeg" || t === ".jpg" || t === ".jpeg") labels.push("JPEG");
    else if (t === "image/png" || t === ".png") labels.push("PNG");
    else labels.push(t);
  });
  if (labels.length === 0) return "";
  return `Formatos permitidos: ${labels.join(", ")}`;
}

function isImageFile(file: File): boolean {
  return file.type.startsWith("image/");
}

function validateFile(
  file: File,
  acceptedTypes: string[],
  maxSizeMB: number
): string | undefined {
  if (!isMimeAccepted(file, acceptedTypes)) {
    return "Tipo de archivo no permitido.";
  }
  if (file.size > maxSizeMB * 1024 * 1024) {
    return `El archivo supera el límite de ${maxSizeMB} MB.`;
  }
  return undefined;
}

function loadPreview(file: File): Promise<string | undefined> {
  return new Promise((resolve) => {
    if (!isImageFile(file)) {
      resolve(undefined);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      resolve(reader.result as string);
    };
    reader.onerror = () => resolve(undefined);
    reader.readAsDataURL(file);
  });
}

export function FileUpload({
  accept,
  maxFiles = 5,
  maxSizeMB = 10,
  multiple = true,
  onFilesChange,
  disabled = false,
  className = "",
}: FileUploadProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [dragState, setDragState] = useState<DragState>("idle");
  const inputRef = useRef<HTMLInputElement>(null);
  const acceptedTypes = parseAcceptedMimes(accept);
  const acceptHint = getAcceptHint(accept);

  const updateFiles = useCallback(
    (updated: UploadFile[]) => {
      setFiles(updated);
      onFilesChange(updated);
    },
    [onFilesChange]
  );

  const processIncomingFiles = useCallback(
    async (incoming: File[]) => {
      const remaining = maxFiles - files.length;
      if (remaining <= 0) return;
      const limited = incoming.slice(0, remaining);

      const newEntries: UploadFile[] = await Promise.all(
        limited.map(async (file) => {
          const error = validateFile(file, acceptedTypes, maxSizeMB);
          const preview = error ? undefined : await loadPreview(file);
          return {
            id: crypto.randomUUID(),
            file,
            preview,
            progress: error ? 0 : 0,
            error,
          };
        })
      );

      const merged = [...files, ...newEntries];
      updateFiles(merged);
    },
    [files, maxFiles, acceptedTypes, maxSizeMB, updateFiles]
  );

  const handleDragEnter = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      if (disabled) return;
      const items = Array.from(e.dataTransfer.items);
      const hasInvalid =
        acceptedTypes.length > 0 &&
        items.some(
          (item) =>
            item.kind === "file" &&
            !isMimeAccepted(
              { type: item.type, name: "" } as File,
              acceptedTypes
            )
        );
      setDragState(hasInvalid ? "reject" : "over");
    },
    [disabled, acceptedTypes]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      if (disabled) return;
    },
    [disabled]
  );

  const handleDragLeave = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.currentTarget.contains(e.relatedTarget as Node)) return;
      setDragState("idle");
    },
    []
  );

  const handleDrop = useCallback(
    async (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setDragState("idle");
      if (disabled) return;
      const dropped = Array.from(e.dataTransfer.files);
      if (dropped.length === 0) return;
      await processIncomingFiles(dropped);
    },
    [disabled, processIncomingFiles]
  );

  const handleInputChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = Array.from(e.target.files ?? []);
      if (selected.length === 0) return;
      await processIncomingFiles(selected);
      // Reset input so the same file can be re-added after removal
      e.target.value = "";
    },
    [processIncomingFiles]
  );

  const handleZoneClick = useCallback(() => {
    if (disabled) return;
    inputRef.current?.click();
  }, [disabled]);

  const handleRemove = useCallback(
    (id: string) => {
      const updated = files.filter((f) => f.id !== id);
      updateFiles(updated);
    },
    [files, updateFiles]
  );

  // Drag zone styling
  const zoneBase =
    "relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 px-6 py-10 transition-colors duration-150 cursor-pointer select-none";

  const zoneVariants: Record<DragState, string> = {
    idle: "border-dashed border-slate-300 bg-white hover:border-primary-400 hover:bg-primary-50/40 dark:border-slate-600 dark:bg-slate-900 dark:hover:border-primary-500 dark:hover:bg-primary-900/20",
    over: "border-solid border-primary-500 bg-primary-50 dark:border-primary-400 dark:bg-primary-900/30",
    reject: "border-solid border-red-400 bg-red-50 dark:border-red-500 dark:bg-red-900/20",
  };

  const disabledZone = "opacity-50 pointer-events-none cursor-not-allowed";

  const zoneClasses = [
    zoneBase,
    zoneVariants[dragState],
    disabled ? disabledZone : "",
  ]
    .filter(Boolean)
    .join(" ");

  const atLimit = files.length >= maxFiles;

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {/* Drop zone */}
      <div
        role="button"
        aria-label="Zona de carga de archivos"
        tabIndex={disabled ? -1 : 0}
        className={zoneClasses}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleZoneClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleZoneClick();
          }
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="sr-only"
          onChange={handleInputChange}
          disabled={disabled || atLimit}
          aria-hidden="true"
          tabIndex={-1}
        />

        {/* Icon */}
        <div
          className={`flex h-12 w-12 items-center justify-center rounded-full ${
            dragState === "reject"
              ? "bg-red-100 text-red-500 dark:bg-red-900/40"
              : dragState === "over"
              ? "bg-primary-100 text-primary-600 dark:bg-primary-800/50"
              : "bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500"
          }`}
        >
          <Upload className="h-6 w-6" aria-hidden="true" />
        </div>

        {/* Label */}
        <div className="text-center">
          {dragState === "over" ? (
            <p className="text-sm font-medium text-primary-600 dark:text-primary-400">
              Suelta los archivos aquí
            </p>
          ) : dragState === "reject" ? (
            <p className="text-sm font-medium text-red-500 dark:text-red-400">
              Tipo de archivo no permitido
            </p>
          ) : (
            <>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Arrastra archivos aquí o{" "}
                <span className="text-primary-600 underline underline-offset-2 dark:text-primary-400">
                  haz clic para seleccionar
                </span>
              </p>
              {acceptHint && (
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  {acceptHint}
                </p>
              )}
              <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                Máximo {maxSizeMB} MB por archivo · hasta {maxFiles} archivo
                {maxFiles !== 1 ? "s" : ""}
              </p>
            </>
          )}
        </div>

        {atLimit && (
          <p className="absolute bottom-2 left-0 right-0 text-center text-xs text-amber-500 dark:text-amber-400">
            Límite de {maxFiles} archivo{maxFiles !== 1 ? "s" : ""} alcanzado
          </p>
        )}
      </div>

      {/* File list */}
      {files.length > 0 && (
        <ul className="flex flex-col gap-2" role="list" aria-label="Archivos seleccionados">
          {files.map((entry) => (
            <li
              key={entry.id}
              className={`relative flex items-start gap-3 rounded-lg border p-3 ${
                entry.error
                  ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20"
                  : "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50"
              }`}
            >
              {/* Thumbnail or icon */}
              <div className="flex-shrink-0">
                {entry.preview ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={entry.preview}
                    alt={entry.file.name}
                    className="h-10 w-10 rounded object-cover"
                  />
                ) : isImageFile(entry.file) ? (
                  <div className="flex h-10 w-10 items-center justify-center rounded bg-slate-200 text-slate-400 dark:bg-slate-700 dark:text-slate-500">
                    <ImageIcon className="h-5 w-5" aria-hidden="true" />
                  </div>
                ) : (
                  <div className="flex h-10 w-10 items-center justify-center rounded bg-slate-200 text-slate-400 dark:bg-slate-700 dark:text-slate-500">
                    <FileText className="h-5 w-5" aria-hidden="true" />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p
                    className="truncate text-sm font-medium text-slate-700 dark:text-slate-200"
                    title={entry.file.name}
                  >
                    {entry.file.name}
                  </p>
                  <button
                    type="button"
                    aria-label={`Eliminar ${entry.file.name}`}
                    onClick={() => handleRemove(entry.id)}
                    className="flex-shrink-0 rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-300"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>

                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  {formatFileSize(entry.file.size)}
                </p>

                {/* Error message */}
                {entry.error && (
                  <p className="mt-1 text-xs font-medium text-red-500 dark:text-red-400">
                    {entry.error}
                  </p>
                )}

                {/* Progress bar */}
                {!entry.error && (
                  <div
                    className="mt-2 h-1 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
                    role="progressbar"
                    aria-valuenow={entry.progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`Progreso de ${entry.file.name}`}
                  >
                    <div
                      className="h-full rounded-full bg-primary-500 transition-all duration-300 ease-in-out"
                      style={{ width: `${entry.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
